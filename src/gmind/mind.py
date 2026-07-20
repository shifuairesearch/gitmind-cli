from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from .client import GitMindClient, GitMindError
from .markdown import normalize_content, parse_markdown_outline


DEFAULT_BACKUP_DIR = Path.home() / ".local" / "share" / "gmind" / "backups"


def safe_name(name: str, fallback: str = "mind") -> str:
    value = (name or fallback).strip() or fallback
    value = re.sub(r'[/\\:*?"<>|]', "_", value)
    return value[:100]


def fetch_json_url(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"Accept": "application/json,text/plain,*/*"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def read_mind(client: GitMindClient, file_guid: str) -> tuple[dict[str, Any], dict[str, Any]]:
    meta = client.get(f"/minds/{file_guid}")
    if meta.get("status") != 200:
        raise GitMindError(f"read mind failed: {meta.get('message')}", payload=meta)
    project_url = (meta.get("data") or {}).get("project_url")
    if not project_url:
        return meta, normalize_content({"root": {"data": {"text": meta.get("data", {}).get("file_name", "Untitled")}, "children": []}})
    return meta, normalize_content(fetch_json_url(project_url))


def count_nodes(node: dict[str, Any] | None) -> int:
    if not node:
        return 0
    return 1 + sum(count_nodes(child) for child in node.get("children") or [])


def content_summary(content: dict[str, Any]) -> dict[str, Any]:
    root = content.get("root") or {}
    return {
        "root_text": ((root.get("data") or {}).get("text") or "").strip(),
        "node_count": count_nodes(root),
        "root_child_count": len(root.get("children") or []),
        "floating_root_count": len(content.get("floatRoots") or []),
        "rel_line_count": len(content.get("relLines") or []),
        "version": content.get("version"),
    }


def render_markdown(content: dict[str, Any], title: str | None = None) -> str:
    root = content.get("root") or {}
    root_text = ((root.get("data") or {}).get("text") or "").strip()
    lines = [f"# {title or root_text or 'Untitled'}", ""]
    if title and root_text and title != root_text:
        lines.extend([f"_Root: {root_text}_", ""])
    for child in root.get("children") or []:
        render_node(child, 1, lines)
    for floating in content.get("floatRoots") or []:
        lines.extend(["", "## Floating Topic", ""])
        render_node(floating, 1, lines)
    return "\n".join(lines).rstrip() + "\n"


def render_node(node: dict[str, Any], depth: int, lines: list[str]) -> None:
    text = ((node.get("data") or {}).get("text") or "").strip()
    lines.append(f"{'  ' * (depth - 1)}- {text or '(empty)'}")
    for child in node.get("children") or []:
        render_node(child, depth + 1, lines)


def load_content_from_file(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        return normalize_content(json.loads(path.read_text(encoding="utf-8")))
    return parse_markdown_outline(path.read_text(encoding="utf-8"))


def write_export(content: dict[str, Any], fmt: str, out: Path | None, title: str | None = None) -> str | None:
    if fmt == "json":
        text = json.dumps(content, ensure_ascii=False, indent=2) + "\n"
    elif fmt == "md":
        text = render_markdown(content, title=title)
    else:
        raise ValueError(f"unsupported format: {fmt}")
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        return None
    return text


def write_backup(file_item: dict[str, Any], content: dict[str, Any], backup_dir: Path = DEFAULT_BACKUP_DIR) -> tuple[Path, Path]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    file_guid = file_item.get("file_guid") or "unknown"
    base = f"{safe_name(file_item.get('file_name') or file_guid)}-{file_guid}-{stamp}"
    json_path = backup_dir / f"{base}.json"
    md_path = backup_dir / f"{base}.md"
    json_path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(content, title=file_item.get("file_name")), encoding="utf-8")
    return json_path, md_path


def scrub_meta(meta: dict[str, Any]) -> dict[str, Any]:
    data = dict(meta.get("data") or {})
    data.pop("project_url", None)
    return {"status": meta.get("status"), "message": meta.get("message"), "data": data}
