"""Configuration loader for Paper Reading Notes."""

import os
import yaml
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def _read_mineru_token() -> str:
    """Fallback: read token from MinerU.md if not in config."""
    mineru_md = PROJECT_ROOT / "MinerU.md"
    if mineru_md.exists():
        for line in mineru_md.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("eyJ"):
                return line
    return ""


class Settings:
    """Application settings loaded from config.yaml."""

    def __init__(self, config_path: Path | None = None):
        self._path = config_path or DEFAULT_CONFIG_PATH
        self._raw: dict = {}
        self.reload()

    def reload(self):
        if self._path.exists():
            with open(self._path, "r", encoding="utf-8") as f:
                self._raw = yaml.safe_load(f) or {}
        else:
            self._raw = {}

    def save(self):
        with open(self._path, "w", encoding="utf-8") as f:
            yaml.dump(self._raw, f, default_flow_style=False, allow_unicode=True)

    # --- App ---
    @property
    def app_name(self) -> str:
        return self._raw.get("app", {}).get("name", "Paper Reading Notes")

    @property
    def theme(self) -> str:
        return self._raw.get("app", {}).get("theme", "light")

    @theme.setter
    def theme(self, value: str):
        self._raw.setdefault("app", {})["theme"] = value

    @property
    def items_per_page(self) -> int:
        return self._raw.get("app", {}).get("items_per_page", 20)

    # --- MinerU ---
    @property
    def mineru_api_base(self) -> str:
        return self._raw.get("mineru", {}).get(
            "api_base", "https://mineru.net/api/v4"
        )

    @property
    def mineru_token(self) -> str:
        token = self._raw.get("mineru", {}).get("token", "")
        if not token:
            token = _read_mineru_token()
        return token

    @property
    def mineru_model_version(self) -> str:
        return self._raw.get("mineru", {}).get("model_version", "vlm")

    @property
    def mineru_enable_formula(self) -> bool:
        return self._raw.get("mineru", {}).get("enable_formula", True)

    @property
    def mineru_enable_table(self) -> bool:
        return self._raw.get("mineru", {}).get("enable_table", True)

    @property
    def mineru_language(self) -> str:
        return self._raw.get("mineru", {}).get("language", "en")

    @property
    def mineru_poll_interval(self) -> int:
        return self._raw.get("mineru", {}).get("poll_interval", 5)

    @property
    def mineru_poll_timeout(self) -> int:
        return self._raw.get("mineru", {}).get("poll_timeout", 600)

    # --- LLM Providers ---
    @property
    def llm_providers(self) -> list[dict]:
        return self._raw.get("llm_providers", [])

    def get_provider(self, provider_id: str) -> dict | None:
        for p in self.llm_providers:
            if p.get("id") == provider_id:
                return p
        return None

    def get_default_provider(self) -> dict | None:
        default_id = self._raw.get("ai", {}).get("default_provider", "")
        if default_id:
            return self.get_provider(default_id)
        for p in self.llm_providers:
            if p.get("enabled", True):
                return p
        return None

    def get_all_models(self) -> list[dict]:
        """Flat list of all models from all enabled providers."""
        models = []
        for provider in self.llm_providers:
            if not provider.get("enabled", True):
                continue
            for model in provider.get("models", []):
                models.append(
                    {
                        "provider_id": provider["id"],
                        "provider_name": provider.get("name", provider["id"]),
                        "model_id": model["id"],
                        "model_name": model.get("name", model["id"]),
                        "is_default": model.get("is_default", False),
                    }
                )
        return models

    def resolve_model(self, provider_id: str | None, model_id: str | None) -> tuple[dict, dict]:
        """Resolve to (provider_config, model_config). Raises ValueError if not found."""
        if provider_id and model_id:
            provider = self.get_provider(provider_id)
            if not provider:
                raise ValueError(f"Provider '{provider_id}' not found")
            for m in provider.get("models", []):
                if m["id"] == model_id:
                    return provider, m
            raise ValueError(f"Model '{model_id}' not found in provider '{provider_id}'")

        default = self.get_default_provider()
        if not default:
            raise ValueError("No LLM provider configured")
        for m in default.get("models", []):
            if m.get("is_default", False):
                return default, m
        models = default.get("models", [])
        if models:
            return default, models[0]
        raise ValueError(f"No models in provider '{default['id']}'")

    def add_provider(self, provider: dict):
        providers = self._raw.setdefault("llm_providers", [])
        providers.append(provider)
        self.save()

    def update_provider(self, provider_id: str, data: dict):
        for i, p in enumerate(self._raw.get("llm_providers", [])):
            if p.get("id") == provider_id:
                self._raw["llm_providers"][i] = data
                self.save()
                return
        raise ValueError(f"Provider '{provider_id}' not found")

    def remove_provider(self, provider_id: str):
        providers = self._raw.get("llm_providers", [])
        self._raw["llm_providers"] = [p for p in providers if p.get("id") != provider_id]
        self.save()

    # --- AI ---
    @property
    def note_max_tokens(self) -> int:
        return self._raw.get("ai", {}).get("note_max_tokens", 4096)

    @property
    def chat_max_tokens(self) -> int:
        return self._raw.get("ai", {}).get("chat_max_tokens", 2048)

    @property
    def temperature(self) -> float:
        return self._raw.get("ai", {}).get("temperature", 0.3)

    # --- Storage ---
    @property
    def papers_dir(self) -> Path:
        return PROJECT_ROOT / self._raw.get("storage", {}).get("papers_dir", "papers")

    @property
    def notes_dir(self) -> Path:
        return PROJECT_ROOT / self._raw.get("storage", {}).get("notes_dir", "notes")

    @property
    def uploads_dir(self) -> Path:
        return PROJECT_ROOT / self._raw.get("storage", {}).get("uploads_dir", "data/uploads")

    @property
    def database_path(self) -> Path:
        return PROJECT_ROOT / self._raw.get("database", {}).get("path", "data/paper_reading.db")


# Global singleton
settings = Settings()
