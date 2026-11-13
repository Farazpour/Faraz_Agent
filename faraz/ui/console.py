import sys
import re
import textwrap
from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown


def _force_utf8():
    """Force UTF-8 on the Windows console before any output happens."""
    if sys.platform == "win32":
        try:
            import ctypes
            k32 = ctypes.windll.kernel32
            k32.SetConsoleOutputCP(65001)
            k32.SetConsoleCP(65001)
        except Exception:
            pass
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_force_utf8()

# ── RTL / Persian display support ────────────────────────────────────────
# Classic Windows consoles (conhost) do not shape or reorder Arabic script,
# so Persian text shows up with disconnected, reversed letters. We reshape it
# and apply the bidi algorithm before printing. Set FARAZ_RTL=0 to disable.
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _RTL_OK = True
except Exception:
    _RTL_OK = False

import os as _os
RTL_ENABLED = _RTL_OK and _os.environ.get("FARAZ_RTL", "1") != "0"
_ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")


def _rtl_line(line: str) -> str:
    if not RTL_ENABLED or not _ARABIC_RE.search(line):
        return line
    try:
        return get_display(arabic_reshaper.reshape(line))
    except Exception:
        return line


def rtl_text(text: str, width: int = None) -> str:
    """Applies RTL shaping per line, leaving fenced code blocks untouched.

    Lines are wrapped to the console width *before* reordering, otherwise the
    terminal would read the paragraph bottom-up across wrapped lines.
    """
    if not RTL_ENABLED:
        return text
    width = width or max(20, (console.width or 80) - 2)
    out = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence or not _ARABIC_RE.search(line):
            out.append(line)
            continue
        chunks = textwrap.wrap(
            line,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
            replace_whitespace=False,
            drop_whitespace=False,
        ) or [""]
        out.extend(_rtl_line(chunk) for chunk in chunks)
    return "\n".join(out)


# Claude Code aesthetic theme
custom_theme = Theme({
    "info": "dim cyan",
    "warning": "yellow",
    "danger": "bold red",
    "success": "bold green",
    "brand": "bold #D97706",         # Claude-like warm amber
    "brand_light": "#FBBF24",
    "dim_gray": "#6B7280",
    "tool_title": "bold #38BDF8",     # Sky blue
    "tool_box": "#1E293B",
    "diff_add": "green",
    "diff_remove": "red",
})

console = Console(theme=custom_theme, highlight=True)
err_console = Console(theme=custom_theme, stderr=True)

def print_banner_line():
    console.print("[dim_gray]" + "─" * (console.width or 80) + "[/dim_gray]")

def print_markdown(content: str):
    """Renders formatted markdown inside terminal."""
    md = Markdown(rtl_text(content), code_theme="monokai")
    console.print(md)

def print_agent_thought(thought: str):
    """Prints internal reasoning or thought block in subdued tone."""
    if thought.strip():
        panel = Panel(
            Text(rtl_text(thought.strip()), style="dim italic"),
            title="[dim]Thought[/dim]",
            border_style="dim_gray",
            padding=(0, 1),
        )
        console.print(panel)

def print_tool_start(tool_name: str, args_summary: str):
    """Prints tool invocation bar."""
    text = Text.assemble(
        (" ⚙ ", "tool_title"),
        (f"Executing: {tool_name} ", "bold white"),
        (f"({args_summary})", "dim_gray")
    )
    console.print(text)

def print_tool_result(result_text: str, success: bool = True):
    """Displays truncated or clean preview of tool result."""
    lines = result_text.splitlines()
    display_lines = lines[:15]
    truncated = len(lines) > 15
    
    body = "\n".join(display_lines)
    if truncated:
        body += f"\n... [{len(lines) - 15} more lines omitted]"
        
    border = "green" if success else "red"
    panel = Panel(
        Text(rtl_text(body), style="dim white"),
        border_style=border,
        title="[dim]Result[/dim]",
        padding=(0, 1)
    )
    console.print(panel)

def print_error(msg: str):
    console.print(f"[danger]✖ Error:[/danger] {msg}")

def print_success(msg: str):
    console.print(f"[success]✔[/success] {msg}")

def print_warning(msg: str):
    console.print(f"[warning]⚠[/warning] {msg}")
