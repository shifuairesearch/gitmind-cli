from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


CONFIG_DIR = Path(os.environ.get("GMIND_CONFIG_DIR", Path.home() / ".config" / "gmind"))
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass(frozen=True)
class TokenInfo:
    token: str | None
    source: str | None


def normalize_token(token: str | None) -> str | None:
    if not token:
        return None
    cleaned = token.strip()
    if not cleaned:
        return None
    if cleaned.lower().startswith("authorization:"):
        cleaned = cleaned.split(":", 1)[1].strip()
    if cleaned.startswith("v2,"):
        cleaned = f"Bearer {cleaned}"
    return cleaned


def redact_token(token: str | None) -> str | None:
    token = normalize_token(token)
    if not token:
        return None
    if len(token) <= 18:
        return "<redacted>"
    return f"{token[:16]}...{token[-6:]}"


def load_token(explicit_token: str | None = None) -> TokenInfo:
    explicit = normalize_token(explicit_token)
    if explicit:
        return TokenInfo(explicit, "--token")
    env_token = normalize_token(os.environ.get("GITMIND_TOKEN"))
    if env_token:
        return TokenInfo(env_token, "GITMIND_TOKEN")
    if CONFIG_FILE.exists():
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        file_token = normalize_token(data.get("bearer_token") or data.get("api_token"))
        if file_token:
            return TokenInfo(file_token, str(CONFIG_FILE))
    return TokenInfo(None, None)


def save_token(token: str, source: str = "manual") -> Path:
    normalized = normalize_token(token)
    if not normalized:
        raise ValueError("empty GitMind token")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps({"bearer_token": normalized, "source": source}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    try:
        CONFIG_FILE.chmod(0o600)
    except OSError:
        pass
    return CONFIG_FILE
