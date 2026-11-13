from pathlib import Path
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style

SLASH_COMMANDS = [
    "/help",
    "/menu",
    "/models",
    "/model",
    "/key",
    "/agent",
    "/mode",
    "/chats",
    "/chat",
    "/history",
    "/file",
    "/save",
    "/auto-approve",
    "/providers",
    "/clear",
    "/compact",
    "/config",
    "/tokens",
    "/exit",
    "/quit",
]

style = Style.from_dict({
    "prompt": "#F59E0B bold",
    "prompt-sign": "#D97706 bold",
    "agent-prompt": "#10B981 bold",
    "agent-sign": "#059669 bold",
    "command": "#38BDF8",
})

def create_prompt_session() -> PromptSession:
    """Configures prompt_toolkit session with persistent history and completions."""
    history_dir = Path.home() / ".agent_faraz"
    history_dir.mkdir(parents=True, exist_ok=True)
    history_file = history_dir / "history.txt"
    
    completer = WordCompleter(SLASH_COMMANDS, ignore_case=True, match_middle=False)
    
    return PromptSession(
        history=FileHistory(str(history_file)),
        auto_suggest=AutoSuggestFromHistory(),
        completer=completer,
        style=style,
        multiline=False,
    )

def get_prompt_text(model_name: str, mode: str = "chat") -> list:
    """Returns styled prompt label with Faraz: in chat mode and Agent Faraz Agent: in agent mode."""
    if mode == "agent":
        return [
            ("class:agent-prompt", "Agent Faraz Agent:"),
            ("class:agent-sign", " ❯ "),
        ]
    return [
        ("class:prompt", "Faraz:"),
        ("class:prompt-sign", " ❯ "),
    ]
