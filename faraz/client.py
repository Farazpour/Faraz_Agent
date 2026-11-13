import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from faraz.config import AgentConfig, DEFAULT_PROVIDERS
from faraz.tools import TOOLS_OPENAI_SCHEMA, TOOLS_ANTHROPIC_SCHEMA

@dataclass
class ToolCallRequest:
    id: str
    name: str
    arguments: Dict[str, Any]

@dataclass
class LLMResponse:
    content: Optional[str]
    tool_calls: List[ToolCallRequest]
    finish_reason: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0

def clean_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Removes null/irrelevant keys so strict APIs (Groq/OpenAI) accept them.

    `tool_calls` may only appear on assistant messages and `tool_call_id` only
    on tool messages. Older session files stored them as null on every message,
    which triggers a 400 error.
    """
    cleaned = []
    for m in messages:
        role = m.get("role")
        out = {"role": role, "content": m.get("content") or ""}
        if role == "assistant" and m.get("tool_calls"):
            out["tool_calls"] = m["tool_calls"]
        if role == "tool" and m.get("tool_call_id"):
            out["tool_call_id"] = m["tool_call_id"]
        cleaned.append(out)
    return cleaned


class LLMClient:
    """Unified client supporting both OpenAI-compatible endpoints (Ollama, LM Studio, DeepSeek) and Anthropic."""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.provider = config.provider.lower()
        self.model = config.model
        self._init_backend()

    def _init_backend(self):
        if self.provider == "anthropic":
            import anthropic
            api_key = self.config.get_api_key("anthropic")
            if not api_key:
                raise ValueError("Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable or save with /config.")
            self.anthropic_client = anthropic.Anthropic(api_key=api_key)
            self.openai_client = None
        else:
            from openai import OpenAI
            base_url = self.config.get_base_url()
            api_key = self.config.get_api_key()
            if not api_key:
                if self.provider in ("ollama", "lmstudio"):
                    api_key = "dummy-key"
                else:
                    meta = DEFAULT_PROVIDERS.get(self.provider, {})
                    env_var = meta.get("api_key_env", f"{self.provider.upper()}_API_KEY")
                    raise ValueError(
                        f"API key for '{self.provider}' not found!\n"
                        f"Use '/key <your_api_key>' in the chat or set {env_var} in your environment."
                    )
            self.openai_client = OpenAI(base_url=base_url, api_key=api_key)
            self.anthropic_client = None

    def create_chat_completion(self, messages: List[Dict[str, Any]]) -> LLMResponse:
        """Dispatches chat request to selected provider with tool definitions."""
        if self.provider == "anthropic":
            return self._call_anthropic(messages)
        else:
            return self._call_openai(messages)

    def _call_openai(self, messages: List[Dict[str, Any]]) -> LLMResponse:
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=clean_messages(messages),
                tools=TOOLS_OPENAI_SCHEMA,
                tool_choice="auto",
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            
            choice = response.choices[0]
            msg = choice.message
            
            tool_calls = []
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                    except Exception:
                        args = {"raw": tc.function.arguments}
                    tool_calls.append(ToolCallRequest(
                        id=tc.id or f"call_{len(tool_calls)}",
                        name=tc.function.name,
                        arguments=args
                    ))

            in_tok = response.usage.prompt_tokens if response.usage else 0
            out_tok = response.usage.completion_tokens if response.usage else 0

            return LLMResponse(
                content=msg.content or "",
                tool_calls=tool_calls,
                finish_reason=choice.finish_reason,
                input_tokens=in_tok,
                output_tokens=out_tok
            )
        except Exception as e:
            err_msg = str(e)
            if "credits remaining" in err_msg or "insufficient_quota" in err_msg or "billing" in err_msg:
                raise PermissionError(
                    "OpenAI Error: Your account has $0 credits remaining!\n"
                    "OpenAI requires adding credit ($5) at https://platform.openai.com/settings/organization/billing/\n"
                    "Alternatively, you can use Groq for FREE: /model groq llama-3.3-70b-versatile"
                )
            if "Connection refused" in err_msg or "Failed to connect" in err_msg or "Connection error" in err_msg:
                if self.provider == "ollama":
                    raise ConnectionError("Could not connect to Ollama at http://localhost:11434. Make sure Ollama is running ('ollama serve') or switch to OpenAI using: /model openai")
                elif self.provider == "lmstudio":
                    raise ConnectionError("Could not connect to LM Studio at http://localhost:1234. Make sure the local server is started or switch provider using: /model openai")
                elif self.provider == "openai":
                    raise ConnectionError("Could not connect to OpenAI (api.openai.com). Please check your internet connection or proxy settings.")
            raise e

    def _call_anthropic(self, messages: List[Dict[str, Any]]) -> LLMResponse:
        # Separate system message if present
        messages = clean_messages(messages)
        system_prompt = ""
        anthropic_msgs = []
        for m in messages:
            if m["role"] == "system":
                system_prompt = m["content"]
            elif m["role"] == "tool":
                # Convert tool role to tool_result user message block
                anthropic_msgs.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": m.get("tool_call_id", "call_0"),
                        "content": m.get("content", ""),
                    }]
                })
            elif m["role"] == "assistant" and "tool_calls" in m:
                # Convert assistant tool_calls to tool_use blocks
                blocks = []
                if m.get("content"):
                    blocks.append({"type": "text", "text": m["content"]})
                for tc in m["tool_calls"]:
                    blocks.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]
                    })
                anthropic_msgs.append({"role": "assistant", "content": blocks})
            else:
                anthropic_msgs.append({"role": m["role"], "content": m["content"]})

        response = self.anthropic_client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=anthropic_msgs,
            tools=TOOLS_ANTHROPIC_SCHEMA,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )

        content_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCallRequest(
                    id=block.id,
                    name=block.name,
                    arguments=block.input
                ))

        in_tok = response.usage.input_tokens if response.usage else 0
        out_tok = response.usage.output_tokens if response.usage else 0

        return LLMResponse(
            content="\n".join(content_parts),
            tool_calls=tool_calls,
            finish_reason=response.stop_reason,
            input_tokens=in_tok,
            output_tokens=out_tok
        )
