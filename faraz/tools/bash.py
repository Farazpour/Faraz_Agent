import os
import shlex
import subprocess
from typing import Dict, Any, Tuple
from faraz.ui.console import console

DANGEROUS_PATTERNS = [
    "rm -rf",
    "del /s",
    "rmdir /s",
    "format ",
    "git reset --hard",
    "git clean -fd",
    "drop table",
    "drop database",
    ":(){ :|:& };:", # forkbomb
]

def is_potentially_destructive(command: str) -> bool:
    """Checks if a command matches common destructive patterns."""
    cmd_lower = command.lower()
    return any(p in cmd_lower for p in DANGEROUS_PATTERNS)

def execute_command(
    command: str,
    timeout: int = 60,
    cwd: str = ".",
    auto_approve: bool = False,
    require_confirmation: bool = True
) -> Dict[str, Any]:
    """
    Executes a shell command in the workspace safely.
    Prompts user if command looks destructive or auto_approve is False.
    """
    cmd_clean = command.strip()
    
    # Check confirmation
    if require_confirmation and is_potentially_destructive(cmd_clean):
        console.print(f"\n[bold red]⚠ Warning:[/bold red] Agent wants to run a potentially destructive command:")
        console.print(f"[bold yellow]  $ {cmd_clean}[/bold yellow]")
        confirm = input("Allow execution? (y/N): ").strip().lower()
        if confirm not in ("y", "yes"):
            return {
                "success": False,
                "stdout": "",
                "stderr": "Command execution rejected by user.",
                "exit_code": -1
            }

    try:
        # On Windows, use shell=True (PowerShell / cmd)
        is_windows = os.name == "nt"
        process = subprocess.run(
            cmd_clean,
            shell=True,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        
        output = process.stdout
        if process.stderr:
            output += ("\n[STDERR]\n" + process.stderr) if output else process.stderr
            
        return {
            "success": process.returncode == 0,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "output": output or "(No output from command)",
            "exit_code": process.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds.",
            "output": f"Command timed out after {timeout} seconds.",
            "exit_code": 124
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "output": f"Execution error: {str(e)}",
            "exit_code": -1
        }
