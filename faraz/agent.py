import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from faraz.config import AgentConfig
from faraz.prompts import get_system_prompt
from faraz.client import LLMClient, ToolCallRequest
from faraz.tools import dispatch_tool
from faraz.session import ChatSessionManager
from rich.text import Text
from faraz.ui.console import (
    console,
    print_markdown,
    print_tool_start,
    print_tool_result,
    print_error,
    print_success,
    print_agent_thought,
)

class AgentFaraz:
    """Core autonomous engineering agent with ReAct execution loop."""

    def __init__(self, config: AgentConfig, workspace_path: Optional[Path] = None):
        self.config = config
        self.workspace_path = workspace_path or Path.cwd()
        self.client = LLMClient(config)
        self.messages: List[Dict[str, Any]] = []
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.mode = config.active_mode or "chat"
        self.session_id = config.active_chat_id or ChatSessionManager.generate_id()
        self.session_title = "New Chat"
        self.load_or_init_session()

    def init_system_prompt(self):
        """Initializes or resets system instructions with active mode."""
        self.messages = [
            {"role": "system", "content": get_system_prompt(self.workspace_path, self.mode)}
        ]

    def load_or_init_session(self):
        """Restores past session if exists, otherwise initiates fresh prompt."""
        saved = ChatSessionManager.load_session(self.session_id)
        if saved and saved.get("messages"):
            self.session_title = saved.get("title", "Saved Chat")
            self.mode = saved.get("mode", self.mode)
            self.messages = [
                {"role": "system", "content": get_system_prompt(self.workspace_path, self.mode)}
            ]
            for m in saved.get("messages", []):
                if m.get("role") == "system":
                    continue
                role = m.get("role")
                entry = {"role": role, "content": m.get("content") or ""}
                if role == "assistant" and m.get("tool_calls"):
                    entry["tool_calls"] = m["tool_calls"]
                if role == "tool" and m.get("tool_call_id"):
                    entry["tool_call_id"] = m["tool_call_id"]
                self.messages.append(entry)
        else:
            self.init_system_prompt()

    def set_mode(self, mode: str):
        """Switches between 'chat' and 'agent' mode and updates system prompt."""
        self.mode = mode
        self.config.active_mode = mode
        self.config.save()
        if self.messages and self.messages[0].get("role") == "system":
            self.messages[0]["content"] = get_system_prompt(self.workspace_path, self.mode)
        else:
            self.messages.insert(0, {"role": "system", "content": get_system_prompt(self.workspace_path, self.mode)})

    def save_current_session(self):
        """Persists current dialogue to session storage."""
        ChatSessionManager.save_session(
            session_id=self.session_id,
            title=self.session_title,
            messages=self.messages,
            provider=self.config.provider,
            model=self.config.model,
            mode=self.mode
        )
        self.config.active_chat_id = self.session_id
        self.config.save()

    def new_session(self, title: Optional[str] = None):
        """Starts a clean, new chat session."""
        self.save_current_session()
        self.session_id = ChatSessionManager.generate_id()
        self.session_title = title or "New Chat"
        self.init_system_prompt()
        self.save_current_session()

    def switch_to_session(self, session_data: Dict[str, Any]):
        """Switches to an existing session from history."""
        self.save_current_session()
        self.session_id = session_data.get("id", ChatSessionManager.generate_id())
        self.session_title = session_data.get("title", "Saved Chat")
        self.mode = session_data.get("mode", self.mode)
        self.load_or_init_session()
        self.save_current_session()

    def reset(self):
        """Clears conversation history."""
        self.init_system_prompt()
        self.save_current_session()
        console.print("[dim]Conversation history cleared.[/dim]")

    def compact(self):
        """Compacts prior conversation history into a concise summary."""
        if len(self.messages) <= 2:
            console.print("[dim]Conversation is too short to compact.[/dim]")
            return

        with console.status("[brand]Faraz is compacting conversation context...[/brand]", spinner="dots"):
            summary_prompt = [
                {"role": "system", "content": "You are a concise technical summarizer."},
                {
                    "role": "user",
                    "content": f"Summarize key decisions, code changes, and open tasks from this dialogue:\n{json.dumps(self.messages[1:])}"
                }
            ]
            res = self.client.create_chat_completion(summary_prompt)
            summary = res.content or "Prior conversation summary."
            
            # Keep system prompt + summary as first user message
            self.messages = [
                {"role": "system", "content": get_system_prompt(self.workspace_path, self.mode)},
                {"role": "user", "content": f"[Context Summary of prior work]\n{summary}"},
                {"role": "assistant", "content": "Understood. I have preserved context and am ready to proceed."}
            ]
            self.save_current_session()
            
        print_success("Context successfully compacted.")

    def run_turn(self, user_input: str):
        """Executes one multi-step turn for the user input."""
        # Auto-generate title from first prompt if new
        if self.session_title == "New Chat" and user_input:
            clean_t = user_input.strip().replace("\n", " ")
            self.session_title = clean_t[:35] + ("..." if len(clean_t) > 35 else "")

        self.messages.append({"role": "user", "content": user_input})
        max_steps = 15
        step = 0

        config_opts = {
            "timeout": self.config.command_timeout_seconds,
            "auto_approve": self.config.auto_approve_commands,
            "require_confirmation": self.config.require_confirmation_for_destructive,
        }

        while step < max_steps:
            step += 1
            
            think_label = "Agent Faraz Agent is thinking..." if self.mode == "agent" else "Faraz is thinking..."
            try:
                with console.status(f"[brand]{think_label}[/brand]", spinner="dots"):
                    response = self.client.create_chat_completion(self.messages)
            except KeyboardInterrupt:
                console.print("\n[yellow]Generation cancelled by user.[/yellow]")
                return
            except Exception as e:
                print_error(str(e))
                return

            self.total_input_tokens += response.input_tokens
            self.total_output_tokens += response.output_tokens

            # Render textual response if present
            if response.content and response.content.strip():
                if self.mode == "agent":
                    console.print(Text("Agent Faraz Agent:", style="bold #10B981"))
                else:
                    console.print(Text("Faraz:", style="bold #F59E0B"))
                print_markdown(response.content.strip())
                console.print()

            # If no tools requested, turn is complete
            if not response.tool_calls:
                self.messages.append({"role": "assistant", "content": response.content or ""})
                break

            # Format assistant message with tool calls
            tool_call_dicts = []
            for tc in response.tool_calls:
                tool_call_dicts.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments) if isinstance(tc.arguments, dict) else str(tc.arguments)
                    }
                })

            self.messages.append({
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": tool_call_dicts
            })

            # Execute requested tools
            for tc in response.tool_calls:
                args_summary = ", ".join(f"{k}='{v}'" if len(str(v)) < 30 else f"{k}=..." for k, v in tc.arguments.items())
                print_tool_start(tc.name, args_summary)

                tool_label = f"Agent Faraz Agent is running {tc.name}..." if self.mode == "agent" else f"Faraz is running {tc.name}..."
                try:
                    with console.status(f"[brand]{tool_label}[/brand]", spinner="line"):
                        result_str = dispatch_tool(tc.name, tc.arguments, config_opts)
                except KeyboardInterrupt:
                    result_str = json.dumps({"error": "Tool execution aborted by user."})
                    console.print("[yellow]Tool execution cancelled by user.[/yellow]")
                except Exception as e:
                    result_str = json.dumps({"error": f"Failed: {str(e)}"})

                # Print formatted preview of result
                try:
                    res_json = json.loads(result_str)
                    success = res_json.get("success", True)
                    # Pretty preview for user
                    if "output" in res_json:
                        print_tool_result(res_json["output"], success=success)
                    elif "content" in res_json:
                        print_tool_result(res_json["content"][:600], success=success)
                    elif "tree" in res_json:
                        print_tool_result(res_json["tree"], success=success)
                    elif "matches" in res_json:
                        print_tool_result(res_json["matches"], success=success)
                    elif "message" in res_json:
                        print_tool_result(res_json["message"], success=success)
                    else:
                        print_tool_result(result_str[:400], success=success)
                except Exception:
                    print_tool_result(result_str[:400], success=True)

                # Record tool output in history
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str
                })

        # Save session automatically after turn completes
        self.save_current_session()

        if self.config.show_token_usage and (self.total_input_tokens > 0 or self.total_output_tokens > 0):
            console.print(
                f"[dim_gray]Tokens: {self.total_input_tokens} in / {self.total_output_tokens} out[/dim_gray]"
            )
