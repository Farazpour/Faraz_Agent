import json
from typing import Dict, Any, List
from faraz.tools.bash import execute_command
from faraz.tools.file_ops import read_file, write_file, edit_file
from faraz.tools.search import list_directory, search_files

# OpenAI / Ollama compatible function schemas
TOOLS_OPENAI_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a terminal shell command (bash, powershell, git, npm, python, etc.) in the current workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The exact shell command line string to execute."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file contents with line numbers and optional line range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative or absolute path to the file."
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Optional starting line number (1-based)."
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Optional ending line number (inclusive)."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create a new file or completely overwrite an existing file with given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to create or overwrite."
                    },
                    "content": {
                        "type": "string",
                        "description": "Complete content to write into the file."
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace a specific exact target string with a replacement string in an existing file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to edit."
                    },
                    "target": {
                        "type": "string",
                        "description": "The exact character sequence to replace, including exact whitespace and indentation."
                    },
                    "replacement": {
                        "type": "string",
                        "description": "The replacement string."
                    }
                },
                "required": ["path", "target", "replacement"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and directories in a tree structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list (default: current directory '.')."
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Whether to list subdirectories recursively (default: false)."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for a keyword or regex pattern across files in the directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex or text pattern to search for."
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory path to start searching from (default: '.')."
                    }
                },
                "required": ["pattern"]
            }
        }
    }
]

# Anthropic format converter
TOOLS_ANTHROPIC_SCHEMA = [
    {
        "name": t["function"]["name"],
        "description": t["function"]["description"],
        "input_schema": t["function"]["parameters"],
    }
    for t in TOOLS_OPENAI_SCHEMA
]

def dispatch_tool(name: str, args: Dict[str, Any], config_opts: Dict[str, Any] = None) -> str:
    """Dispatches tool execution and formats result as string."""
    config_opts = config_opts or {}
    try:
        if name == "run_command":
            res = execute_command(
                command=args.get("command", ""),
                timeout=config_opts.get("timeout", 60),
                auto_approve=config_opts.get("auto_approve", False),
                require_confirmation=config_opts.get("require_confirmation", True)
            )
            return json.dumps(res, indent=2)

        elif name == "read_file":
            res = read_file(
                path=args.get("path", ""),
                start_line=args.get("start_line"),
                end_line=args.get("end_line")
            )
            return json.dumps(res, indent=2)

        elif name == "write_file":
            res = write_file(
                path=args.get("path", ""),
                content=args.get("content", ""),
                auto_approve=config_opts.get("auto_approve", False),
                require_confirmation=config_opts.get("require_confirmation", True)
            )
            return json.dumps(res, indent=2)

        elif name == "edit_file":
            res = edit_file(
                path=args.get("path", ""),
                target=args.get("target", ""),
                replacement=args.get("replacement", ""),
                auto_approve=config_opts.get("auto_approve", False),
                require_confirmation=config_opts.get("require_confirmation", True)
            )
            return json.dumps(res, indent=2)

        elif name == "list_directory":
            res = list_directory(
                path=args.get("path", "."),
                recursive=args.get("recursive", False)
            )
            return json.dumps(res, indent=2)

        elif name == "search_files":
            res = search_files(
                pattern=args.get("pattern", ""),
                path=args.get("path", ".")
            )
            return json.dumps(res, indent=2)

        else:
            return json.dumps({"error": f"Unknown tool '{name}'."})
    except Exception as e:
        return json.dumps({"error": f"Execution failed: {str(e)}"})
