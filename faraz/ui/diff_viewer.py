import difflib
from rich.panel import Panel
from rich.text import Text
from faraz.ui.console import console

def display_diff(filename: str, original_content: str, new_content: str):
    """Renders a visual unified diff in Claude Code style."""
    orig_lines = original_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    
    diff = list(difflib.unified_diff(
        orig_lines,
        new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        n=3
    ))
    
    if not diff:
        console.print(f"[dim]No changes in {filename}[/dim]")
        return

    diff_text = Text()
    added_count = 0
    removed_count = 0

    for line in diff:
        line_clean = line.rstrip("\n")
        if line.startswith("+++") or line.startswith("---"):
            diff_text.append(f"{line_clean}\n", style="bold cyan")
        elif line.startswith("@@"):
            diff_text.append(f"{line_clean}\n", style="bold magenta")
        elif line.startswith("+"):
            added_count += 1
            diff_text.append(f"{line_clean}\n", style="green")
        elif line.startswith("-"):
            removed_count += 1
            diff_text.append(f"{line_clean}\n", style="red")
        else:
            diff_text.append(f"{line_clean}\n", style="dim white")

    title = f"[bold white]{filename}[/bold white] ([green]+{added_count}[/green], [red]-{removed_count}[/red])"
    panel = Panel(
        diff_text,
        title=title,
        border_style="#D97706",
        padding=(0, 1)
    )
    console.print(panel)
