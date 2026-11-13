import sys
import argparse
from pathlib import Path
from faraz.config import AgentConfig, DEFAULT_PROVIDERS
from faraz.agent import AgentFaraz
from faraz.session import ChatSessionManager
from faraz.tools.file_ops import read_file
from faraz.ui.console import console, print_error, print_success, print_warning, _force_utf8
from faraz.ui.banners import show_welcome_banner, show_help_menu
from faraz.ui.menu import (
    show_model_menu,
    show_chat_history,
    show_agent_mission_banner,
    run_interactive_model_wizard,
    POPULAR_PRESETS
)
from faraz.ui.prompt import create_prompt_session, get_prompt_text
from faraz import __version__

def handle_slash_command(command: str, agent: AgentFaraz, config: AgentConfig) -> bool:
    """Processes interactive slash commands. Returns True if handled."""
    parts = command.strip().split()
    cmd = parts[0].lower()
    args = parts[1:]

    # ── Exit ────────────────────────────────────────────────────────────
    if cmd in ("/exit", "/quit"):
        agent.save_current_session()
        config.save()
        console.print("[dim]Goodbye from Agent Faraz! Settings and session saved.[/dim]")
        sys.exit(0)

    # ── Help ────────────────────────────────────────────────────────────
    elif cmd == "/help":
        show_help_menu()
        return True

    # ── Interactive Model Menu & History ────────────────────────────────
    elif cmd in ("/menu", "/models"):
        run_interactive_model_wizard(config, agent)
        return True

    elif cmd == "/model":
        if not args:
            run_interactive_model_wizard(config, agent)
            return True

        first_arg = args[0].strip()
        clean_arg = first_arg.strip("[]()<> \"'").strip()
        switched = False

        from faraz.config import PRESET_MAP

        # 1. Switch by recent history index (e.g. /model 1 or /model 2 or /model [1])
        if clean_arg.isdigit():
            idx = int(clean_arg) - 1
            recent = config.recent_models or []
            if 0 <= idx < len(recent):
                config.provider = recent[idx]["provider"]
                config.model = recent[idx]["model"]
                switched = True
            else:
                print_error(f"Invalid model number '{clean_arg}'. Choose between 1 and {len(recent)}.")
                return True

        # 2. Switch by preset code (e.g. /model P5 or /model [P5])
        elif clean_arg.upper() in PRESET_MAP:
            p_prov, p_mod = PRESET_MAP[clean_arg.upper()]
            config.provider = p_prov
            config.model = p_mod
            switched = True

        # 3. Switch by provider name (e.g. /model ollama or /model groq)
        elif clean_arg.lower() in DEFAULT_PROVIDERS:
            config.provider = clean_arg.lower()
            if len(args) > 1:
                sub_mod = args[1].strip().strip("[]\"'")
                if sub_mod.upper() in PRESET_MAP:
                    _, sub_mod = PRESET_MAP[sub_mod.upper()]
                config.model = sub_mod
            else:
                config.model = DEFAULT_PROVIDERS[config.provider]["default_model"]
            switched = True

        # 4. Switch custom model name under current provider
        else:
            raw_mod = clean_arg
            if raw_mod.upper() in PRESET_MAP:
                p_prov, raw_mod = PRESET_MAP[raw_mod.upper()]
                config.provider = p_prov
            config.model = raw_mod
            switched = True

        if switched:
            config.sanitize_model()
            config.record_recent_model(config.provider, config.model)
            try:
                agent.client = agent.client.__class__(config)
                print_success(f"Switched & saved! Provider: [cyan]{config.provider.upper()}[/cyan] | Model: [green]{config.model}[/green]")
            except Exception as e:
                print_warning(f"Saved to config, but backend warned: {str(e)}")
        return True

    # ── API Key Management ──────────────────────────────────────────────
    elif cmd == "/key":
        if not args:
            current_key = config.get_api_key()
            masked = f"{current_key[:7]}...{current_key[-4:]}" if current_key and len(current_key) > 12 else ("(not set)" if not current_key else "***")
            console.print(f"Current Provider: [cyan]{config.provider}[/cyan] | Key: [green]{masked}[/green]")
            console.print("Usage: [yellow]/key <your_api_key>[/yellow]  or  [yellow]/key <provider> <your_api_key>[/yellow]")
            return True

        raw_text = "".join(args).replace("<", "").replace(">", "").strip()
        first_arg = args[0].lower().replace("<", "").replace(">", "").strip()

        target_provider = None
        new_key = None

        if first_arg in DEFAULT_PROVIDERS and len(args) > 1:
            target_provider = first_arg
            new_key = "".join(args[1:]).replace("<", "").replace(">", "").strip()
        else:
            new_key = raw_text
            if new_key.startswith("sk-ant-"):
                target_provider = "anthropic"
            elif new_key.startswith("gsk_"):
                target_provider = "groq"
            elif new_key.startswith("sk-or-"):
                target_provider = "openrouter"
            elif new_key.startswith("sk-"):
                target_provider = "openai"
            else:
                target_provider = config.provider if config.provider in DEFAULT_PROVIDERS else "openai"

        if config.provider in ("ollama", "lmstudio") or config.provider != target_provider:
            config.provider = target_provider
            config.model = DEFAULT_PROVIDERS[target_provider]["default_model"]

        config.api_keys[target_provider] = new_key
        config.record_recent_model(config.provider, config.model)
        try:
            config.save()
            agent.client = agent.client.__class__(config)
            print_success(f"Switched provider to [cyan]{target_provider.upper()}[/cyan] (Model: [green]{config.model}[/green])")
            print_success("API key successfully saved!")
        except Exception as e:
            print_error(f"Failed to update key: {str(e)}")
        return True

    # ── Dedicated Agent Mode & Missions ─────────────────────────────────
    elif cmd == "/agent":
        if args:
            task = " ".join(args)
            agent.set_mode("agent")
            show_agent_mission_banner(task)
            agent.run_turn(task)
            return True
        else:
            agent.set_mode("agent")
            print_success("🎯 Switched to [bold green]AGENT MODE[/bold green] (Prompt: Agent Faraz Agent: ❯).")
            return True

    elif cmd == "/mode":
        if not args:
            status_style = "green" if agent.mode == "agent" else "yellow"
            prompt_name = "Agent Faraz Agent:" if agent.mode == "agent" else "Faraz:"
            console.print(f"\n[bold #F59E0B]═══ Agent Faraz Mode & Model Control ═══[/bold #F59E0B]")
            console.print(f"Current Mode: [bold {status_style}]{agent.mode.upper()}[/bold {status_style}] ({prompt_name}) │ Model: [cyan]{config.provider.upper()}[/cyan] / [green]{config.model}[/green]\n")
            console.print("  [bold cyan][1][/bold cyan] 💬 [bold yellow]Chat Mode[/bold yellow]  [dim](Faraz: - Fast interactive Q&A and coding)[/dim]")
            console.print("  [bold cyan][2][/bold cyan] 🎯 [bold green]Agent Mode[/bold green]  [dim](Agent Faraz Agent: - Autonomous multi-step execution)[/dim]")
            console.print("  [bold cyan][3][/bold cyan] 🧠 [bold white]Change Model[/bold white]  [dim](Local Ollama download / Cloud connect)[/dim]")
            console.print("  [bold cyan][0][/bold cyan] ✖  Cancel\n")

            try:
                m_choice = input("Select option (1-3): ").strip()
            except (KeyboardInterrupt, EOFError):
                return True

            if m_choice == "1":
                agent.set_mode("chat")
                print_success("Switched to [bold yellow]CHAT MODE[/bold yellow] (Prompt: Faraz: ❯).")
            elif m_choice == "2":
                agent.set_mode("agent")
                print_success("Switched to [bold green]AGENT MODE[/bold green] (Prompt: Agent Faraz Agent: ❯).")
            elif m_choice == "3":
                run_interactive_model_wizard(config, agent)
            return True

        target_arg = args[0].lower()
        if target_arg in ("agent", "autonomous", "a"):
            agent.set_mode("agent")
            print_success("🎯 Switched to [bold green]AGENT MODE[/bold green] (Prompt: Agent Faraz Agent: ❯).")
            return True
        elif target_arg in ("chat", "normal", "c"):
            agent.set_mode("chat")
            print_success("💬 Switched to [bold yellow]CHAT MODE[/bold yellow] (Prompt: Faraz: ❯).")
            return True
        elif target_arg in DEFAULT_PROVIDERS or target_arg.isdigit() or target_arg.startswith("p"):
            return handle_slash_command(f"/model {' '.join(args)}", agent, config)
        else:
            console.print("Usage: /mode chat  or  /mode agent  or  /model")
            return True

    # ── Multi-Session Chat History ──────────────────────────────────────
    elif cmd in ("/chats", "/history"):
        sessions = ChatSessionManager.list_sessions()
        show_chat_history(sessions, active_id=agent.session_id)
        return True

    elif cmd == "/chat":
        if not args:
            sessions = ChatSessionManager.list_sessions()
            show_chat_history(sessions, active_id=agent.session_id)
            return True

        subcmd = args[0].lower()
        subargs = args[1:]

        if subcmd == "new":
            title = " ".join(subargs) if subargs else None
            agent.new_session(title=title)
            print_success(f"Started new chat session: [cyan]{agent.session_title}[/cyan]")
            return True

        elif subcmd == "switch":
            if not subargs:
                console.print("Usage: /chat switch <number or chat_id>")
                return True
            target_id = subargs[0]
            sessions = ChatSessionManager.list_sessions()
            target_session = None

            if target_id.isdigit():
                idx = int(target_id) - 1
                if 0 <= idx < len(sessions):
                    target_session = sessions[idx]
            else:
                target_session = ChatSessionManager.load_session(target_id)

            if target_session:
                agent.switch_to_session(target_session)
                msg_count = len(agent.messages) - 1
                print_success(f"Switched to chat: [cyan]{agent.session_title}[/cyan] ({msg_count} messages loaded)")
            else:
                print_error(f"Chat session '{target_id}' not found.")
            return True

        elif subcmd == "delete":
            if not subargs:
                console.print("Usage: /chat delete <number or chat_id>")
                return True
            target_id = subargs[0]
            sessions = ChatSessionManager.list_sessions()
            del_id = target_id
            if target_id.isdigit():
                idx = int(target_id) - 1
                if 0 <= idx < len(sessions):
                    del_id = sessions[idx].get("id", "")
            
            if ChatSessionManager.delete_session(del_id):
                print_success(f"Deleted chat session '{del_id}'.")
                # If deleted active session, start a new one
                if del_id == agent.session_id:
                    agent.new_session()
            else:
                print_error(f"Could not delete chat session '{del_id}'.")
            return True

        elif subcmd == "rename":
            if not subargs:
                console.print("Usage: /chat rename <new_title>")
                return True
            agent.session_title = " ".join(subargs)
            agent.save_current_session()
            print_success(f"Chat renamed to: [cyan]{agent.session_title}[/cyan]")
            return True

        else:
            console.print("Unknown /chat action. Use: /chat new, /chat switch, /chat delete, or /chats")
            return True

    # ── Manual System File Access ───────────────────────────────────────
    elif cmd == "/file":
        if not args:
            console.print("Usage: [yellow]/file <file_path>[/yellow]  (e.g. /file C:\\Users\\Faraz\\notes.txt or /file main.py)")
            return True
        file_path_str = " ".join(args)
        res = read_file(file_path_str)
        if res.get("success"):
            agent.messages.append({
                "role": "user",
                "content": f"[User attached file: {res['path']}]\n```{res['content']}```"
            })
            agent.save_current_session()
            tag = "[bold cyan]🌐 System File[/bold cyan]" if res.get("is_system_path") else "[bold green]Workspace File[/bold green]"
            print_success(f"{tag} attached to Faraz's context: [cyan]{res['path']}[/cyan] ({res['total_lines']} lines)")
        else:
            print_error(res.get("error", "Failed to read file."))
        return True

    # ── Session & Cache Utilities ───────────────────────────────────────
    elif cmd == "/clear":
        agent.reset()
        return True

    elif cmd == "/compact":
        agent.compact()
        return True

    elif cmd == "/tokens":
        console.print(f"[bold cyan]Total Usage:[/bold cyan] {agent.total_input_tokens} prompt tokens, {agent.total_output_tokens} completion tokens.")
        return True

    elif cmd == "/save":
        config.save()
        agent.save_current_session()
        print_success(f"All settings and active session saved! (Provider: [cyan]{config.provider}[/cyan], Model: [green]{config.model}[/green])")
        return True

    elif cmd in ("/auto-approve", "/y"):
        if args and args[0].lower() in ("off", "false", "0"):
            config.auto_approve_commands = False
        else:
            config.auto_approve_commands = True
        config.save()
        status_text = "[green]ON (Non-destructive shell commands run automatically)[/green]" if config.auto_approve_commands else "[yellow]OFF (Confirmation required)[/yellow]"
        console.print(f"Auto-approve: {status_text} (Saved)")
        return True

    elif cmd == "/providers":
        console.print("[bold yellow]Supported Providers & Defaults:[/bold yellow]")
        for key, p in DEFAULT_PROVIDERS.items():
            active = " [bold green](ACTIVE)[/bold green]" if key == config.provider else ""
            console.print(f"  • [bold white]{key.upper()}[/bold white]: {p.get('name')} | Default Model: [cyan]{p.get('default_model')}[/cyan]{active}")
        console.print("\nSwitch provider using: [yellow]/model <provider> [model_name][/yellow] or view [yellow]/menu[/yellow]")
        return True

    elif cmd == "/config":
        console.print("[bold yellow]Current Configuration:[/bold yellow]")
        console.print(f"  • Version: V{__version__}")
        console.print(f"  • Provider: {config.provider.upper()}")
        console.print(f"  • Model: {config.model}")
        console.print(f"  • Mode: {agent.mode.upper()}")
        console.print(f"  • Active Session: {agent.session_title} ({agent.session_id})")
        console.print(f"  • Base URL: {config.get_base_url() or '(default)'}")
        has_key = bool(config.get_api_key())
        console.print(f"  • API Key Configured: {'[green]Yes[/green]' if has_key else '[red]No (Run /key <api_key>)[/red]'}")
        console.print(f"  • Auto Approve Commands: {config.auto_approve_commands}")
        console.print(f"  • Require Confirmation for Destructive: {config.require_confirmation_for_destructive}")
        console.print(f"  • Timeout: {config.command_timeout_seconds}s")
        return True

    return False

def main():
    _force_utf8()
    parser = argparse.ArgumentParser(
        description=f"Agent Faraz V{__version__} - Autonomous Terminal AI Agent"
    )
    parser.add_argument("prompt", nargs="*", help="Optional initial instruction or question")
    parser.add_argument("-m", "--model", help="Specify model name (e.g. qwen2.5-coder:7b, gemma4:12b, gpt-4o)")
    parser.add_argument("-p", "--provider", help="Specify provider (ollama, lmstudio, anthropic, openai, deepseek, groq)")
    parser.add_argument("-k", "--api-key", help="Specify and save API key for provider")
    parser.add_argument("-a", "--agent", action="store_true", help="Launch directly in autonomous Agent Mode")
    parser.add_argument("-y", "--auto-approve", action="store_true", help="Auto-approve non-destructive shell commands")
    parser.add_argument("-v", "--version", action="version", version=f"Agent Faraz V{__version__}")

    args = parser.parse_args()

    # Load configuration
    config = AgentConfig.load()
    config_changed = False
    if args.provider:
        config.provider = args.provider.lower()
        if not args.model and config.provider in DEFAULT_PROVIDERS:
            config.model = DEFAULT_PROVIDERS[config.provider]["default_model"]
        config_changed = True
    if args.model:
        config.model = args.model
        config_changed = True
    if args.api_key:
        config.api_keys[config.provider] = args.api_key
        config_changed = True
    if args.agent:
        config.active_mode = "agent"
        config_changed = True
    if args.auto_approve:
        config.auto_approve_commands = True
        config_changed = True

    if config_changed:
        config.record_recent_model(config.provider, config.model)
        config.save()

    workspace_dir = Path.cwd()
    agent = AgentFaraz(config, workspace_path=workspace_dir)

    # Always default to chat mode on launch unless --agent flag explicitly passed
    if not args.agent:
        agent.set_mode("chat")

    # If single-shot prompt provided on command line (e.g. faraz "analyze this file")
    if args.prompt:
        initial_query = " ".join(args.prompt)
        if args.agent:
            show_agent_mission_banner(initial_query)
        agent.run_turn(initial_query)
        return

    # Interactive REPL session
    show_welcome_banner(config.provider, config.model, workspace_dir, mode=agent.mode)
    prompt_session = create_prompt_session()

    while True:
        try:
            prompt_fragments = get_prompt_text(config.model, mode=agent.mode)
            user_input = prompt_session.prompt(prompt_fragments)

            if not user_input or not user_input.strip():
                continue

            cleaned_input = user_input.strip()

            # Handle slash commands
            if cleaned_input.startswith("/"):
                handled = handle_slash_command(cleaned_input, agent, config)
                if handled:
                    continue

            # In Agent Mode, show mission banner
            if agent.mode == "agent":
                show_agent_mission_banner(cleaned_input)

            # Execute turn
            agent.run_turn(cleaned_input)

        except KeyboardInterrupt:
            console.print("\n[dim]Press Ctrl+D or type /exit to leave.[/dim]")
            continue
        except EOFError:
            agent.save_current_session()
            config.save()
            console.print("\n[dim]Goodbye from Agent Faraz! Settings and session saved.[/dim]")
            break
        except Exception as e:
            print_error(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
