import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

DEFAULT_CONFIG_DIR = Path.home() / ".agent_faraz"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.json"

DEFAULT_PROVIDERS = {
    "ollama": {
        "name": "Ollama (Local)",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
        "default_model": "qwen2.5-coder:14b",
    },
    "lmstudio": {
        "name": "LM Studio (Local)",
        "base_url": "http://localhost:1234/v1",
        "api_key": "lm-studio",
        "default_model": "qwen2.5-coder",
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "base_url": "https://api.anthropic.com",
        "api_key_env": "ANTHROPIC_API_KEY",
        "default_model": "claude-3-5-sonnet-20241022",
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "default_model": "gpt-4o",
    },
    "deepseek": {
        "name": "DeepSeek API",
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
    },
    "groq": {
        "name": "Groq Cloud",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "default_model": "openai/gpt-oss-120b",
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "default_model": "anthropic/claude-3.5-sonnet",
    },
}

PRESET_MAP = {
    "P1": ("ollama", "qwen2.5-coder:7b"),
    "P2": ("ollama", "gemma4:12b"),
    "P3": ("groq", "openai/gpt-oss-120b"),
    "P4": ("openai", "gpt-4o"),
    "P5": ("anthropic", "claude-3-5-sonnet-20241022"),
    "P6": ("deepseek", "deepseek-flash"),
}

class AgentConfig(BaseModel):
    provider: str = Field(default="ollama", description="Active LLM provider")
    model: str = Field(default="qwen2.5-coder:14b", description="Model identifier")
    custom_base_url: Optional[str] = Field(default=None, description="Custom base URL for OpenAI-compatible endpoints")
    api_keys: Dict[str, str] = Field(default_factory=dict, description="Stored API keys by provider")
    recent_models: list = Field(default_factory=list, description="Previously connected models history")
    active_mode: str = Field(default="chat", description="Active interaction mode: 'chat' or 'agent'")
    active_chat_id: Optional[str] = Field(default=None, description="Currently active chat session ID")
    
    # Execution & Safety
    auto_approve_commands: bool = Field(default=False, description="Auto-approve non-destructive bash commands")
    require_confirmation_for_destructive: bool = Field(default=True, description="Prompt before running dangerous commands")
    command_timeout_seconds: int = Field(default=60, description="Max command runtime before timeout")
    temperature: float = Field(default=0.2, description="Sampling temperature")
    max_tokens: int = Field(default=4096, description="Max output tokens per step")
    
    # UI Options
    theme: str = Field(default="claude", description="Terminal UI theme")
    show_token_usage: bool = Field(default=True, description="Display token counts after completion")

    def record_recent_model(self, provider: str, model: str):
        """Remembers model in recent connection history (max 10 unique)."""
        prov = provider.lower().strip()
        mod = model.strip().strip("[]\"'")
        # Resolve if preset code was passed
        if mod.upper() in PRESET_MAP:
            prov, mod = PRESET_MAP[mod.upper()]
        
        # Filter out existing duplicate or invalid shortcut entries
        self.recent_models = [
            m for m in self.recent_models
            if m.get("model", "").strip("[]\"'").upper() not in PRESET_MAP
            and not (m.get("provider", "").lower() == prov and m.get("model", "") == mod)
        ]
        # Insert at the beginning
        self.recent_models.insert(0, {"provider": prov, "model": mod})
        if len(self.recent_models) > 10:
            self.recent_models = self.recent_models[:10]
        self.save()

    def sanitize_model(self):
        """Ensures model is an exact model name and not a shortcut code like [P5] or P5."""
        clean = self.model.strip("[]()<> \"'").upper()
        if clean in PRESET_MAP:
            prov, mod = PRESET_MAP[clean]
            self.provider = prov
            self.model = mod
            self.save()
        # Clean any shortcut code entries in recent_models as well
        cleaned_recent = []
        for m in self.recent_models:
            m_mod = m.get("model", "").strip("[]()<> \"'")
            if m_mod.upper() in PRESET_MAP:
                p, real_m = PRESET_MAP[m_mod.upper()]
                if not any(r.get("provider") == p and r.get("model") == real_m for r in cleaned_recent):
                    cleaned_recent.append({"provider": p, "model": real_m})
            else:
                if not any(r.get("provider") == m.get("provider") and r.get("model") == m.get("model") for r in cleaned_recent):
                    cleaned_recent.append(m)
        self.recent_models = cleaned_recent

    def get_api_key(self, provider: Optional[str] = None) -> Optional[str]:
        prov = provider or self.provider
        # 1. Check explicitly saved key
        if prov in self.api_keys and self.api_keys[prov]:
            return self.api_keys[prov]
        
        # 2. Check standard environment variable
        meta = DEFAULT_PROVIDERS.get(prov, {})
        env_var = meta.get("api_key_env")
        if env_var and os.environ.get(env_var):
            return os.environ[env_var]
        
        # 3. Check fallback static key (like 'ollama')
        if meta.get("api_key"):
            return meta["api_key"]
            
        return None

    def get_base_url(self, provider: Optional[str] = None) -> Optional[str]:
        if self.custom_base_url:
            return self.custom_base_url
        prov = provider or self.provider
        meta = DEFAULT_PROVIDERS.get(prov, {})
        return meta.get("base_url")

    def save(self, path: Optional[Path] = None):
        """Persists the current configuration both globally and to the local workspace."""
        # 1. Global config (~/.agent_faraz/config.json)
        target = path or DEFAULT_CONFIG_PATH
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(self.model_dump_json(indent=2))
        except Exception:
            pass

        # 2. Local workspace config (.faraz.json in current directory)
        try:
            workspace_cfg = Path.cwd() / ".faraz.json"
            with open(workspace_cfg, "w", encoding="utf-8") as f:
                f.write(self.model_dump_json(indent=2))
        except Exception:
            pass

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "AgentConfig":
        # 1. Local workspace config
        workspace_cfg = Path.cwd() / ".faraz.json"
        if workspace_cfg.exists():
            try:
                with open(workspace_cfg, "r", encoding="utf-8") as f:
                    cfg = cls.model_validate_json(f.read())
                    cfg.sanitize_model()
                    if not cfg.recent_models and cfg.provider and cfg.model:
                        cfg.recent_models.append({"provider": cfg.provider, "model": cfg.model})
                    return cfg
            except Exception:
                pass

        # 2. Global user config
        target = path or DEFAULT_CONFIG_PATH
        try:
            if target.exists():
                with open(target, "r", encoding="utf-8") as f:
                    cfg = cls.model_validate_json(f.read())
                    cfg.sanitize_model()
                    if not cfg.recent_models and cfg.provider and cfg.model:
                        cfg.recent_models.append({"provider": cfg.provider, "model": cfg.model})
                    return cfg
        except Exception:
            pass

        # 3. Default fallback
        config = cls()
        config.sanitize_model()
        # Check if ANTHROPIC_API_KEY or OPENAI_API_KEY is present in env, auto-switch if Ollama is not default
        if os.environ.get("ANTHROPIC_API_KEY"):
            config.provider = "anthropic"
            config.model = DEFAULT_PROVIDERS["anthropic"]["default_model"]
        elif os.environ.get("OPENAI_API_KEY"):
            config.provider = "openai"
            config.model = DEFAULT_PROVIDERS["openai"]["default_model"]
        if config.provider and config.model:
            config.recent_models = [{"provider": config.provider, "model": config.model}]
        return config
