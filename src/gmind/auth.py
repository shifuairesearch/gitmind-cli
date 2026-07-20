from __future__ import annotations

import re
from pathlib import Path

from .client import GitMindClient, GitMindError
from .config import normalize_token, save_token


BROWSER_PROFILES = {
    "comet": Path.home() / "Library" / "Application Support" / "Comet" / "Default",
    "chrome": Path.home() / "Library" / "Application Support" / "Google" / "Chrome" / "Default",
}

TOKEN_PATTERNS = (
    re.compile(rb"Bearer\s+v2,[0-9]+,[0-9]+,[A-Za-z0-9._~+/-]+"),
    re.compile(rb"v2,[0-9]+,[0-9]+,[A-Za-z0-9._~+/-]{16,}"),
)


def iter_leveldb_files(profile: Path):
    leveldb = profile / "Local Storage" / "leveldb"
    if not leveldb.exists():
        return
    yield from leveldb.glob("*.ldb")
    yield from leveldb.glob("*.log")


def find_browser_tokens(browser: str) -> list[str]:
    profile = BROWSER_PROFILES.get(browser)
    if not profile:
        raise ValueError(f"unsupported browser: {browser}")
    tokens: list[str] = []
    for path in iter_leveldb_files(profile) or []:
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if b"gitmind" not in data and b"aoscdn" not in data and b"api_token" not in data:
            continue
        for pattern in TOKEN_PATTERNS:
            for match in pattern.finditer(data):
                token = normalize_token(match.group(0).decode("utf-8", "ignore"))
                if token and token not in tokens:
                    tokens.append(token)
    return tokens


def validate_token(token: str) -> tuple[bool, str]:
    try:
        payload = GitMindClient(token).get("/files", {"per_page": 1})
    except GitMindError as exc:
        return False, str(exc)
    if payload.get("status") == 200:
        return True, "success"
    return False, payload.get("message") or "validation failed"


def import_from_browser(browser: str) -> tuple[Path, str]:
    tokens = find_browser_tokens(browser)
    errors: list[str] = []
    for token in reversed(tokens):
        ok, message = validate_token(token)
        if ok:
            return save_token(token, source=f"browser:{browser}"), message
        errors.append(message)
    if not tokens:
        raise ValueError(f"no GitMind token found in {browser} profile")
    raise ValueError(f"found {len(tokens)} token candidate(s), but none validated: {errors[-1]}")
