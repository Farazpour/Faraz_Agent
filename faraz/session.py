import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

CHATS_DIR = Path.home() / ".agent_faraz" / "chats"

def get_chats_dir() -> Path:
    CHATS_DIR.mkdir(parents=True, exist_ok=True)
    return CHATS_DIR

class ChatSessionManager:
    """Manages persistent chat conversations and multi-session switching."""

    @staticmethod
    def generate_id() -> str:
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_rand = uuid.uuid4().hex[:4]
        return f"chat_{now}_{short_rand}"

    @classmethod
    def list_sessions(cls) -> List[Dict[str, Any]]:
        """Returns all saved sessions sorted by last updated descending."""
        d = get_chats_dir()
        sessions = []
        for file in d.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    sessions.append(data)
            except Exception:
                pass
        
        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
        return sessions

    @classmethod
    def load_session(cls, session_id: str) -> Optional[Dict[str, Any]]:
        """Loads a session by full ID or short prefix."""
        d = get_chats_dir()
        # Direct match
        target = d / f"{session_id}.json"
        if target.exists():
            try:
                with open(target, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        
        # Prefix match
        for file in d.glob("*.json"):
            if file.stem.startswith(session_id):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
        return None

    @classmethod
    def save_session(
        cls,
        session_id: str,
        title: str,
        messages: List[Dict[str, Any]],
        provider: str,
        model: str,
        mode: str = "chat"
    ):
        """Saves or updates a chat session to disk."""
        d = get_chats_dir()
        target = d / f"{session_id}.json"
        
        # Filter messages to preserve essential context without massive bloat
        clean_messages = []
        for m in messages:
            entry = {
                "role": m.get("role"),
                "content": m.get("content", ""),
            }
            if m.get("tool_calls"):
                entry["tool_calls"] = m["tool_calls"]
            if m.get("tool_call_id"):
                entry["tool_call_id"] = m["tool_call_id"]
            clean_messages.append(entry)

        # Count actual user/assistant exchanges
        turns = sum(1 for m in clean_messages if m.get("role") == "user")

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        existing_created = now_str
        if target.exists():
            try:
                with open(target, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    existing_created = old_data.get("created_at", now_str)
            except Exception:
                pass

        data = {
            "id": session_id,
            "title": title or "Untitled Chat",
            "created_at": existing_created,
            "updated_at": now_str,
            "provider": provider,
            "model": model,
            "mode": mode,
            "turns": turns,
            "messages": clean_messages
        }

        try:
            with open(target, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @classmethod
    def delete_session(cls, session_id: str) -> bool:
        """Deletes a session file by ID or prefix."""
        d = get_chats_dir()
        target = d / f"{session_id}.json"
        if target.exists():
            target.unlink()
            return True
        for file in d.glob("*.json"):
            if file.stem.startswith(session_id):
                file.unlink()
                return True
        return False
