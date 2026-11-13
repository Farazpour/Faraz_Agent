import os
import re
from pathlib import Path
from typing import Dict, Any, List

IGNORED_DIRS = {
    ".git", ".svn", ".hg", "__pycache__", "node_modules",
    ".venv", "venv", "env", ".idea", ".vscode", "dist", "build", ".next"
}

def list_directory(path: str = ".", recursive: bool = False, max_depth: int = 2) -> Dict[str, Any]:
    """Lists files and folders in directory tree format."""
    root = Path(path)
    if not root.exists():
        return {"success": False, "error": f"Path '{path}' does not exist."}
    if not root.is_dir():
        return {"success": False, "error": f"Path '{path}' is not a directory."}

    entries = []
    
    def scan(current_dir: Path, current_depth: int):
        if current_depth > max_depth:
            return
        try:
            items = sorted(current_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            for item in items:
                if item.name in IGNORED_DIRS or item.name.startswith("."):
                    continue
                rel_path = item.relative_to(root)
                indent = "  " * (current_depth - 1)
                if item.is_dir():
                    entries.append(f"{indent}📁 {rel_path}/")
                    if recursive:
                        scan(item, current_depth + 1)
                else:
                    entries.append(f"{indent}📄 {rel_path}")
        except PermissionError:
            pass

    scan(root, 1)
    
    return {
        "success": True,
        "path": str(root),
        "total_items": len(entries),
        "tree": "\n".join(entries) if entries else "(Empty directory)"
    }

def search_files(pattern: str, path: str = ".", max_matches: int = 50) -> Dict[str, Any]:
    """Searches for regex or keyword pattern across files."""
    root = Path(path)
    if not root.exists():
        return {"success": False, "error": f"Path '{path}' does not exist."}

    regex = re.compile(pattern, re.IGNORECASE)
    matches: List[str] = []

    for root_dir, dirs, files in os.walk(root):
        # Filter out ignored directories in-place
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

        for file in files:
            if file.startswith("."):
                continue
            file_path = Path(root_dir) / file
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, start=1):
                        if regex.search(line):
                            rel_p = file_path.relative_to(root)
                            matches.append(f"{rel_p}:{line_num}: {line.strip()}")
                            if len(matches) >= max_matches:
                                break
            except Exception:
                pass
        if len(matches) >= max_matches:
            break

    return {
        "success": True,
        "pattern": pattern,
        "matches_count": len(matches),
        "matches": "\n".join(matches) if matches else f"No matches found for '{pattern}'."
    }
