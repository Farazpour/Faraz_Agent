import os
import subprocess
from pathlib import Path
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.align import Align
from rich.rule import Rule
from rich import box
from faraz.ui.console import console
from faraz import __version__

ASCII_LOGO = r"""
  ███████╗ █████╗ ██████╗  █████╗ ███████╗
  ██╔════╝██╔══██╗██╔══██╗██╔══██╗╚══███╔╝
  █████╗  ███████║██████╔╝███████║  ███╔╝ 
  ██╔══╝  ██╔══██║██╔══██╗██╔══██║ ███╔╝  
  ██║     ██║  ██║██║  ██║██║  ██║███████╗
  ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝

   █████╗   ██████╗  ███████╗ ███╗  ██╗████████╗
  ██╔══██╗ ██╔════╝  ██╔════╝ ████╗ ██║╚══██╔══╝
  ███████║ ██║  ███╗ █████╗   ██╔██╗██║   ██║   
  ██╔══██║ ██║   ██║ ██╔══╝   ██║╚████║   ██║   
  ██║  ██║ ╚██████╔╝ ███████╗ ██║ ╚███║   ██║   
  ╚═╝  ╚═╝  ╚═════╝  ╚══════╝ ╚═╝  ╚══╝   ╚═╝   
"""

def get_git_branch() -> str:
    """Returns current git branch if in a git repository."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return ""

def show_welcome_banner(provider: str, model: str, workspace_path: Path, mode: str = "chat"):
    """Displays a stunning large ASCII launch banner."""
    from faraz.config import PRESET_MAP
    clean_m = model.strip("[]\"'")
    if clean_m.upper() in PRESET_MAP:
        provider, model = PRESET_MAP[clean_m.upper()]

    git_branch = get_git_branch()
    branch_str = f" [cyan]git:({git_branch})[/cyan]" if git_branch else ""

    # ── ASCII Logo ──────────────────────────────────────────────
    logo_text = Text(ASCII_LOGO, style="bold #F59E0B", justify="center")
    console.print(Align.center(logo_text))

    # ── Tagline ─────────────────────────────────────────────────
    console.print(Align.center(
        Text("⚡  Autonomous Terminal AI Agent  ⚡", style="bold white")
    ))
    console.print(Align.center(
        Text("Your local & cloud pair-programmer — smarter than the rest.", style="italic #94A3B8")
    ))
    console.print()

    # ── Divider ─────────────────────────────────────────────────
    console.print(Rule(style="#D97706"))
    console.print()

    # ── Info Panel ──────────────────────────────────────────────
    info = Text()
    info.append("  Version   ", style="dim")
    info.append(f"V{__version__}   ", style="bold #F59E0B")
    info.append("│", style="dim #D97706")
    info.append("  Provider  ", style="dim")
    info.append(f"{provider.upper()}   ", style="bold cyan")
    info.append("│", style="dim #D97706")
    info.append("  Model  ", style="dim")
    info.append(f"{model}   ", style="bold green")
    info.append("│", style="dim #D97706")
    info.append("  Mode  ", style="dim")
    mode_color = "green" if mode == "agent" else "yellow"
    info.append(f"{mode.upper()}\n", style=f"bold {mode_color}")
    info.append("  Workspace  ", style="dim")
    info.append(f"{workspace_path}", style="dim white")
    info.append(branch_str)

    console.print(Panel(
        info,
        border_style="#D97706",
        padding=(0, 2),
        box=box.HORIZONTALS,
    ))
    console.print()

    # ── Quick Help ──────────────────────────────────────────────
    hints = Text(justify="center")
    hints.append("/help", style="bold yellow")
    hints.append("  ·  ", style="dim")
    hints.append("/menu", style="bold yellow")
    hints.append("  ·  ", style="dim")
    hints.append("/agent", style="bold green")
    hints.append("  ·  ", style="dim")
    hints.append("/chats", style="bold cyan")
    hints.append("  ·  ", style="dim")
    hints.append("/file", style="bold yellow")
    hints.append("  ·  ", style="dim")
    hints.append("/key", style="bold yellow")
    hints.append("  ·  ", style="dim")
    hints.append("/save", style="bold yellow")
    hints.append("  ·  ", style="dim")
    hints.append("/exit", style="bold yellow")
    console.print(Align.center(hints))
    console.print()
    console.print(Rule(style="#44444A"))
    console.print()

def show_help_menu():
    """Displays slash commands and terminal shortcuts."""
    table = Table(
        title="[bold #F59E0B]Agent Faraz V1.0.0 — Commands & Shortcuts[/bold #F59E0B]",
        border_style="#D97706",
        show_lines=True,
        box=box.ROUNDED,
        header_style="bold #F59E0B",
    )
    table.add_column("Command / Shortcut", style="bold yellow", width=30)
    table.add_column("Description", style="white")

    table.add_row("/help", "Show this interactive command guide")
    table.add_row("/menu , /models", "Interactive Model Selector & history of previously connected models")
    table.add_row("/model [number | name]", "Switch model instantly by history number, preset (P1-P6), or custom name")
    table.add_row("/agent [task]", "Dedicated Agent Mode / Execute autonomous engineering mission")
    table.add_row("/mode [agent | chat]", "Toggle between Autonomous Agent Mode and Interactive Chat Mode")
    table.add_row("/chats , /history", "List and manage all past conversation chat sessions")
    table.add_row("/chat new [title]", "Start a clean, fresh chat session")
    table.add_row("/chat switch <number | id>", "Restore and switch to a previous chat session")
    table.add_row("/chat delete <number | id>", "Delete a previous chat session from history")
    table.add_row("/file <path>", "Manually specify any file on the system (e.g. C:\\... or notes.txt) to attach")
    table.add_row("/key <api_key>", "Save API key securely with automatic provider detection")
    table.add_row("/save", "Permanently save all active configurations and chat session")
    table.add_row("/auto-approve [on | off]", "Toggle auto-approving shell commands and file operations")
    table.add_row("/providers", "List all supported local & cloud providers and configurations")
    table.add_row("/clear", "Reset current conversation context and start fresh")
    table.add_row("/compact", "Summarize prior conversation to save context window tokens")
    table.add_row("/config", "View active configuration settings")
    table.add_row("/tokens", "Show total prompt & completion token usage for this session")
    table.add_row("/exit , /quit", "Gracefully terminate Agent Faraz (saves session & config)")
    table.add_row("Ctrl + C", "Cancel current LLM response or tool execution")
    table.add_row("Alt + Enter / Esc + Enter", "Insert newline for multi-line input")

    console.print()
    console.print(table)
    console.print()
