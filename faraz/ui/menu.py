import os
import shutil
import subprocess
from typing import List, Dict, Any, Optional
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.align import Align
from faraz.ui.console import console, print_success, print_error, print_warning
from faraz.config import AgentConfig, DEFAULT_PROVIDERS

POPULAR_PRESETS = [
    {"num": "P1", "provider": "ollama", "model": "qwen2.5-coder:7b", "desc": "Local (8GB RAM friendly, fast coder)"},
    {"num": "P2", "provider": "ollama", "model": "gemma4:12b", "desc": "Local (Google Gemma on your PC)"},
    {"num": "P3", "provider": "groq", "model": "openai/gpt-oss-120b", "desc": "Cloud (100% Free & ultra-fast)"},
    {"num": "P4", "provider": "openai", "model": "gpt-4o", "desc": "Cloud (OpenAI Flagship)"},
    {"num": "P5", "provider": "anthropic", "model": "claude-3-5-sonnet-20241022", "desc": "Cloud (Claude Code caliber)"},
    {"num": "P6", "provider": "deepseek", "model": "deepseek-flash", "desc": "Cloud (Ultra-cheap & smart)"},
]

RECOMMENDED_LOCAL_MODELS = [
    {"model": "qwen2.5-coder:7b", "desc": "Best Coding Model for 8GB RAM (4.7 GB)"},
    {"model": "llama3.2:3b", "desc": "Ultra-lightweight & Fast (2.0 GB)"},
    {"model": "deepseek-coder:6.7b", "desc": "Strong Code Reasoning (3.8 GB)"},
    {"model": "qwen2.5:7b", "desc": "General Knowledge & Multilingual (4.7 GB)"},
]

def get_installed_ollama_models() -> List[str]:
    """Retrieves list of models currently pulled in Ollama."""
    try:
        res = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            lines = res.stdout.strip().splitlines()
            models = []
            for line in lines[1:]:
                parts = line.split()
                if parts:
                    models.append(parts[0])
            return models
    except Exception:
        pass
    return []

def pull_ollama_model(model_name: str) -> bool:
    """Downloads an Ollama model interactively with real-time terminal progress."""
    console.print(f"\n[bold cyan]📥 Downloading '{model_name}' via Ollama...[/bold cyan]")
    console.print("[dim]Please wait, download progress will display below:[/dim]\n")
    try:
        proc = subprocess.run(["ollama", "pull", model_name])
        return proc.returncode == 0
    except Exception as e:
        console.print(f"[bold red]✖ Download error:[/bold red] {str(e)}")
        return False

def run_interactive_model_wizard(config: AgentConfig, agent: Any) -> bool:
    """
    Guides the user step-by-step:
    - Lists local installed models or prompts to download if missing.
    - Lists cloud providers, asks for choice, and configures automatically.
    """
    console.print()
    console.print(Panel(
        f"[bold #F59E0B]🧠 Agent Faraz — Model Setup Wizard[/bold #F59E0B]\n"
        f"[dim]Active Provider:[/dim] [bold cyan]{config.provider.upper()}[/bold cyan]  │  "
        f"[dim]Model:[/dim] [bold green]{config.model}[/bold green]",
        border_style="#D97706",
        padding=(0, 2)
    ))

    console.print("\n[bold white]Choose your AI backend type:[/bold white]")
    console.print("  [bold cyan][1][/bold cyan] 🖥️  [bold white]Local Models[/bold white]  [dim](Ollama - 100% Free, runs offline on your PC)[/dim]")
    console.print("  [bold cyan][2][/bold cyan] ☁️  [bold white]Cloud Models[/bold white]  [dim](Groq Free, OpenAI, Claude, DeepSeek)[/dim]")
    console.print("  [bold cyan][3][/bold cyan] ⚡ [bold white]Recent Connected Models[/bold white]  [dim](Quick-switch to past models)[/dim]")
    console.print("  [bold cyan][0][/bold cyan] ✖  Cancel\n")

    try:
        choice = input("Enter option (0-3): ").strip()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Cancelled.[/dim]")
        return False

    if choice == "0" or not choice:
        console.print("[dim]Model selection kept unchanged.[/dim]")
        return False

    # ────────────────────────────────────────────────────────────────────
    # 1. LOCAL MODELS (OLLAMA)
    # ────────────────────────────────────────────────────────────────────
    if choice == "1":
        if not shutil.which("ollama"):
            print_error("Ollama is not installed or not in your PATH!")
            console.print("Please install Ollama from [cyan]https://ollama.com[/cyan] first.")
            return False

        installed = get_installed_ollama_models()

        console.print("\n[bold #F59E0B]Local Models Available on your PC & Recommended:[/bold #F59E0B]")
        options = []

        # List installed models first
        if installed:
            console.print("[dim]── Already Downloaded on your PC ──[/dim]")
            for m in installed:
                options.append({"model": m, "installed": True, "desc": "Ready to run immediately"})
                idx = len(options)
                is_active = (config.provider == "ollama" and config.model == m)
                active_badge = " [bold green](ACTIVE)[/bold green]" if is_active else ""
                console.print(f"  [bold cyan][{idx}][/bold cyan] [green]{m}[/green]  [bold green]✔ DOWNLOADED[/bold green]{active_badge}")

        # List recommended models that are not installed yet
        console.print("\n[dim]── Recommended to Download ──[/dim]")
        for rec in RECOMMENDED_LOCAL_MODELS:
            m_name = rec["model"]
            if m_name not in installed:
                options.append({"model": m_name, "installed": False, "desc": rec["desc"]})
                idx = len(options)
                console.print(f"  [bold cyan][{idx}][/bold cyan] [white]{m_name}[/white]  [dim]({rec['desc']})[/dim]")

        # Custom option
        custom_idx = len(options) + 1
        console.print(f"  [bold cyan][{custom_idx}][/bold cyan] [yellow]Enter a custom model name[/yellow]")
        console.print("  [bold cyan][0][/bold cyan] ✖ Cancel\n")

        try:
            sel = input(f"Choose model (1-{custom_idx}): ").strip()
        except (KeyboardInterrupt, EOFError):
            return False

        if sel == "0" or not sel:
            return False

        target_model = None
        needs_download = False

        if sel.isdigit() and 1 <= int(sel) <= len(options):
            chosen_item = options[int(sel) - 1]
            target_model = chosen_item["model"]
            needs_download = not chosen_item["installed"]
        elif sel == str(custom_idx):
            custom_name = input("Enter custom Ollama model name (e.g. llama3.1:8b): ").strip()
            if not custom_name:
                return False
            target_model = custom_name
            needs_download = (target_model not in installed)
        else:
            print_error("Invalid selection.")
            return False

        # If not installed, ask user permission to download!
        if needs_download:
            console.print(f"\n[bold yellow]Model '{target_model}' is not currently downloaded on your system.[/bold yellow]")
            try:
                confirm = input(f"Would you like Agent Faraz to download '{target_model}' now via Ollama? (Y/n): ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                return False

            if confirm not in ("y", "yes", ""):
                console.print("[yellow]Download skipped. Model not changed.[/yellow]")
                return False

            # Run download
            download_ok = pull_ollama_model(target_model)
            if not download_ok:
                print_error(f"Failed to download '{target_model}'.")
                return False
            print_success(f"Model '{target_model}' downloaded successfully!")

        # Activate model
        config.provider = "ollama"
        config.model = target_model
        config.record_recent_model(config.provider, config.model)
        try:
            agent.client = agent.client.__class__(config)
            print_success(f"Connected to Local Model: [green]{target_model}[/green]")
            return True
        except Exception as e:
            print_error(f"Failed to activate local model: {str(e)}")
            return False

    # ────────────────────────────────────────────────────────────────────
    # 2. CLOUD MODELS
    # ────────────────────────────────────────────────────────────────────
    elif choice == "2":
        console.print("\n[bold #38BDF8]Select a Cloud Provider:[/bold #38BDF8]")
        console.print("  [bold cyan][1][/bold cyan]  [bold white]Groq[/bold white]  [bold green](100% FREE & Ultra-fast)[/bold green] — [dim]Llama 3.3 70B[/dim]")
        console.print("  [bold cyan][2][/bold cyan]  [bold white]OpenAI[/bold white]  — [dim]GPT-4o / GPT-4o-mini[/dim]")
        console.print("  [bold cyan][3][/bold cyan]  [bold white]Anthropic Claude[/bold white]  — [dim]Claude 3.5 Sonnet (Claude Code level)[/dim]")
        console.print("  [bold cyan][4][/bold cyan]  [bold white]DeepSeek[/bold white]  — [dim]DeepSeek-Chat (Smart & very cheap)[/dim]")
        console.print("  [bold cyan][5][/bold cyan]  [bold white]OpenRouter[/bold white]  — [dim]Access to all models[/dim]")
        console.print("  [bold cyan][0][/bold cyan] ✖ Cancel\n")

        try:
            cloud_sel = input("Choose cloud provider (1-5): ").strip()
        except (KeyboardInterrupt, EOFError):
            return False

        provider_map = {
            "1": ("groq", "openai/gpt-oss-120b"),
            "2": ("openai", "gpt-4o"),
            "3": ("anthropic", "claude-3-5-sonnet-20241022"),
            "4": ("deepseek", "deepseek-flash"),
            "5": ("openrouter", "anthropic/claude-3.5-sonnet"),
        }

        if cloud_sel not in provider_map:
            if cloud_sel != "0":
                print_error("Invalid choice.")
            return False

        target_provider, default_model = provider_map[cloud_sel]

        # For OpenAI, let user pick between gpt-4o and gpt-4o-mini
        target_model = default_model
        if target_provider == "openai":
            console.print("\n[bold white]Choose OpenAI Model:[/bold white]")
            console.print("  [1] gpt-4o [dim](Flagship smart)[/dim]")
            console.print("  [2] gpt-4o-mini [dim](Fast & economical)[/dim]")
            m_choice = input("Enter choice (1-2) [Default: 1]: ").strip()
            if m_choice == "2":
                target_model = "gpt-4o-mini"
            else:
                target_model = "gpt-4o"

        # Check API key
        existing_key = config.get_api_key(target_provider)
        if not existing_key:
            meta = DEFAULT_PROVIDERS.get(target_provider, {})
            env_var = meta.get("api_key_env", f"{target_provider.upper()}_API_KEY")
            console.print(f"\n[bold yellow]No API key found for {target_provider.upper()}.[/bold yellow]")
            try:
                new_key = input(f"Enter API Key for {target_provider.upper()} (or press Enter to skip): ").strip()
            except (KeyboardInterrupt, EOFError):
                return False

            if new_key:
                clean_k = new_key.replace("<", "").replace(">", "").strip()
                config.api_keys[target_provider] = clean_k
                print_success(f"Saved API key for {target_provider.upper()}!")
            else:
                print_warning(f"No key entered. You can set {env_var} later or use '/key <api_key>'.")

        config.provider = target_provider
        config.model = target_model
        config.record_recent_model(config.provider, config.model)
        try:
            agent.client = agent.client.__class__(config)
            print_success(f"Switched to Cloud Provider: [cyan]{target_provider.upper()}[/cyan] | Model: [green]{target_model}[/green]")
            return True
        except Exception as e:
            print_error(f"Failed to connect: {str(e)}")
            return False

    # ────────────────────────────────────────────────────────────────────
    # 3. RECENT MODELS
    # ────────────────────────────────────────────────────────────────────
    elif choice == "3":
        show_model_menu(config)
        recent = config.recent_models or []
        if not recent:
            return False
        try:
            num = input(f"Enter model number to activate (1-{len(recent)}): ").strip()
        except (KeyboardInterrupt, EOFError):
            return False

        if num.isdigit() and 1 <= int(num) <= len(recent):
            item = recent[int(num) - 1]
            config.provider = item["provider"]
            config.model = item["model"]
            config.record_recent_model(config.provider, config.model)
            try:
                agent.client = agent.client.__class__(config)
                print_success(f"Switched to: [cyan]{config.provider.upper()}[/cyan] | Model: [green]{config.model}[/green]")
                return True
            except Exception as e:
                print_error(str(e))
        return False

    return False

def show_model_menu(config: AgentConfig):
    """Displays recently connected models and available presets with quick-switch numbers."""
    console.print()
    
    # ── Table 1: Recently Connected Models ──
    table = Table(
        title="[bold #F59E0B]⚡ Previously Connected Models[/bold #F59E0B]",
        border_style="#D97706",
        box=box.ROUNDED,
        header_style="bold yellow",
        show_lines=True
    )
    table.add_column("No.", style="bold cyan", width=6, justify="center")
    table.add_column("Provider", style="bold white", width=14)
    table.add_column("Model Name", style="green", width=34)
    table.add_column("Status", style="white", width=14, justify="center")

    recent = config.recent_models or []
    if not recent:
        recent = [{"provider": config.provider, "model": config.model}]

    for idx, item in enumerate(recent, start=1):
        prov = item.get("provider", "")
        mod = item.get("model", "")
        is_active = (prov.lower() == config.provider.lower() and mod.lower() == config.model.lower())
        status = "[bold green]✔ ACTIVE[/bold green]" if is_active else "[dim]Saved[/dim]"
        table.add_row(f"[{idx}]", prov.upper(), mod, status)

    console.print(table)
    console.print()

    # ── Table 2: Quick Presets ──
    preset_table = Table(
        title="[bold #38BDF8]🌐 Popular Presets & Providers[/bold #38BDF8]",
        border_style="#38BDF8",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_lines=True
    )
    preset_table.add_column("Code", style="bold yellow", width=6, justify="center")
    preset_table.add_column("Provider", style="bold white", width=12)
    preset_table.add_column("Model", style="green", width=30)
    preset_table.add_column("Description", style="dim white")

    for p in POPULAR_PRESETS:
        preset_table.add_row(f"[{p['num']}]", p["provider"].upper(), p["model"], p["desc"])

    console.print(preset_table)
    console.print()

    # Instructions
    instructions = Text()
    instructions.append("Switch quickly: ", style="bold white")
    instructions.append("/model <number>", style="bold yellow")
    instructions.append("  (e.g. ", style="dim")
    instructions.append("/model 1", style="bold green")
    instructions.append(" or ", style="dim")
    instructions.append("/model P3", style="bold green")
    instructions.append(")\n", style="dim")
    instructions.append("Or run setup wizard: ", style="bold white")
    instructions.append("/model", style="bold yellow")
    instructions.append("  ·  Add key: ", style="dim")
    instructions.append("/key <api_key>", style="bold yellow")

    console.print(Panel(instructions, border_style="dim_gray", padding=(0, 2)))
    console.print()

def show_chat_history(sessions: List[Dict[str, Any]], active_id: Optional[str] = None):
    """Displays a clean table of all chat sessions for easy switching."""
    console.print()
    table = Table(
        title="[bold #F59E0B]💬 Chat History & Sessions[/bold #F59E0B]",
        border_style="#D97706",
        box=box.ROUNDED,
        header_style="bold yellow",
        show_lines=True
    )
    table.add_column("No.", style="bold cyan", width=6, justify="center")
    table.add_column("Chat Title", style="bold white", width=36)
    table.add_column("Model", style="green", width=22)
    table.add_column("Messages", style="cyan", width=10, justify="center")
    table.add_column("Last Active", style="dim white", width=20)
    table.add_column("Status", style="white", width=12, justify="center")

    if not sessions:
        table.add_row("-", "No previous chat history found", "-", "-", "-", "-")
    else:
        for idx, s in enumerate(sessions, start=1):
            s_id = s.get("id", "")
            title = s.get("title", "Untitled")
            if len(title) > 34:
                title = title[:31] + "..."
            mod = f"{s.get('provider', '')}/{s.get('model', '')}"
            if len(mod) > 20:
                mod = mod[:18] + ".."
            turns = str(s.get("turns", len(s.get("messages", [])) // 2))
            updated = s.get("updated_at", "")
            is_active = (s_id == active_id)
            status = "[bold green]✔ ACTIVE[/bold green]" if is_active else "[dim]Saved[/dim]"
            table.add_row(f"[{idx}]", title, mod, turns, updated, status)

    console.print(table)
    console.print()

    hint = Text()
    hint.append("Switch chat: ", style="bold white")
    hint.append("/chat switch <number or id>", style="bold yellow")
    hint.append("  ·  New chat: ", style="dim")
    hint.append("/chat new [title]", style="bold yellow")
    hint.append("  ·  Delete: ", style="dim")
    hint.append("/chat delete <number>", style="bold yellow")

    console.print(Panel(hint, border_style="dim_gray", padding=(0, 2)))
    console.print()

def show_agent_mission_banner(task: str, mode: str = "agent"):
    """Displays a prominent banner when Agent Mode or an Agent Mission is engaged."""
    text = Text()
    text.append("🎯 AGENT MISSION ACTIVATED\n", style="bold #10B981")
    text.append("Task: ", style="bold white")
    text.append(f"{task}\n", style="italic yellow")
    text.append("Execution: ", style="dim")
    text.append("Autonomous ReAct Loop (Read ➔ Plan ➔ Edit ➔ Execute ➔ Verify)\n", style="dim green")
    text.append("File Access: ", style="dim")
    text.append("Full Workspace & Manual System Paths Enabled", style="dim cyan")

    panel = Panel(
        text,
        border_style="#10B981",
        box=box.DOUBLE,
        padding=(0, 2),
    )
    console.print(panel)
    console.print()
