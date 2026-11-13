import os
from pathlib import Path
from typing import Dict, Any, Optional
from faraz.ui.diff_viewer import display_diff
from faraz.ui.console import console

def resolve_system_path(path_str: str) -> Path:
    """Expands user tilde (~), environment variables, and normalizes absolute or relative paths."""
    clean = path_str.strip().strip('"').strip("'")
    expanded = os.path.expandvars(os.path.expanduser(clean))
    return Path(expanded).resolve()

def is_outside_workspace(file_path: Path, workspace_path: Optional[Path] = None) -> bool:
    """Checks if target path is outside the current project workspace."""
    base = (workspace_path or Path.cwd()).resolve()
    try:
        file_path.relative_to(base)
        return False
    except ValueError:
        return True

def read_file(path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> Dict[str, Any]:
    """Reads a file with line numbering and optional line window from workspace or any system path."""
    file_path = resolve_system_path(path)
    if not file_path.exists():
        return {"success": False, "error": f"File '{path}' does not exist on the system (Resolved: {file_path})."}
    if file_path.is_dir():
        return {"success": False, "error": f"'{path}' is a directory, not a file."}

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            
        total_lines = len(lines)
        s_line = max(1, start_line or 1)
        e_line = min(total_lines, end_line or total_lines)
        
        selected_lines = lines[s_line - 1 : e_line]
        numbered_output = []
        for idx, line in enumerate(selected_lines, start=s_line):
            numbered_output.append(f"{idx:4d} | {line.rstrip()}")
            
        content = "\n".join(numbered_output)
        return {
            "success": True,
            "path": str(file_path),
            "is_system_path": is_outside_workspace(file_path),
            "total_lines": total_lines,
            "lines_shown": f"{s_line}-{e_line}",
            "content": content
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to read file: {str(e)}"}

def write_file(
    path: str,
    content: str,
    auto_approve: bool = False,
    require_confirmation: bool = True
) -> Dict[str, Any]:
    """Creates or overwrites a file in the workspace or across the entire system."""
    file_path = resolve_system_path(path)
    
    # If file is outside current workspace, notify or require user confirmation
    if is_outside_workspace(file_path):
        console.print(f"[bold cyan]🌐 System File Access:[/bold cyan] [yellow]{file_path}[/yellow]")
        if require_confirmation and not auto_approve:
            confirm = input(f"Allow Agent Faraz to write to system file '{file_path}'? (y/N): ").strip().lower()
            if confirm not in ("y", "yes"):
                return {
                    "success": False,
                    "error": f"User denied permission to write to system path '{file_path}'."
                }

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        old_content = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        if old_content:
            display_diff(str(file_path), old_content, content)
            
        return {
            "success": True,
            "path": str(file_path),
            "is_system_path": is_outside_workspace(file_path),
            "message": f"Successfully wrote {len(content)} characters to {file_path}"
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to write file: {str(e)}"}

def edit_file(
    path: str,
    target: str,
    replacement: str,
    auto_approve: bool = False,
    require_confirmation: bool = True
) -> Dict[str, Any]:
    """Replaces target string with replacement inside a workspace or system file and shows diff."""
    file_path = resolve_system_path(path)
    if not file_path.exists():
        return {"success": False, "error": f"File '{path}' not found on the system."}

    # If file is outside current workspace, notify or require confirmation
    if is_outside_workspace(file_path):
        console.print(f"[bold cyan]🌐 System File Access:[/bold cyan] [yellow]{file_path}[/yellow]")
        if require_confirmation and not auto_approve:
            confirm = input(f"Allow Agent Faraz to modify system file '{file_path}'? (y/N): ").strip().lower()
            if confirm not in ("y", "yes"):
                return {
                    "success": False,
                    "error": f"User denied permission to modify system path '{file_path}'."
                }
        
    try:
        original = file_path.read_text(encoding="utf-8")
        if target not in original:
            return {
                "success": False,
                "error": f"Target string not found in '{file_path}'. Please ensure exact whitespace and indentation matching."
            }
            
        updated = original.replace(target, replacement, 1)
        file_path.write_text(updated, encoding="utf-8")
        
        display_diff(str(file_path), original, updated)
        
        return {
            "success": True,
            "path": str(file_path),
            "is_system_path": is_outside_workspace(file_path),
            "message": f"Successfully edited {file_path}"
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to edit file: {str(e)}"}
