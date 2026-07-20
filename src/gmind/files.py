from __future__ import annotations

from collections import deque
from typing import Any

from .client import GitMindClient


def payload_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "items", "list", "records"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    return []


def list_root(client: GitMindClient, per_page: int = 100) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    page = 1
    while page <= 50:
        payload = client.get("/files", {"page": page, "per_page": per_page})
        items = payload_items(payload)
        out.extend(items)
        if len(items) < per_page:
            break
        page += 1
    return out


def list_folder(client: GitMindClient, folder_guid: str) -> list[dict[str, Any]]:
    return payload_items(client.get(f"/files/{folder_guid}"))


def walk_files(client: GitMindClient, max_depth: int | None = None) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    queue = deque([(None, "ROOT", 0, list_root(client))])
    seen_folders: set[str] = set()
    while queue:
        _folder_guid, parent_path, depth, items = queue.popleft()
        for item in items:
            name = item.get("file_name") or item.get("name") or ""
            item_path = f"{parent_path}/{name}" if name else parent_path
            record = dict(item)
            record["path"] = item_path
            results.append(record)
            guid = item.get("guid")
            if item.get("file_type") == 2 and guid and guid not in seen_folders:
                if max_depth is None or depth < max_depth:
                    seen_folders.add(guid)
                    queue.append((guid, item_path, depth + 1, list_folder(client, guid)))
    return results


def slim_file(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "file_name": item.get("file_name"),
        "file_type": item.get("file_type"),
        "guid": item.get("guid"),
        "file_guid": item.get("file_guid"),
        "path": item.get("path"),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
    }


def search_files(client: GitMindClient, term: str, limit: int = 20) -> list[dict[str, Any]]:
    lowered = term.lower()
    matches = [
        item for item in walk_files(client)
        if lowered in (item.get("file_name") or "").lower() or lowered in (item.get("path") or "").lower()
    ]
    return [slim_file(item) for item in matches[:limit]]


def resolve_mind(client: GitMindClient, name_or_guid: str) -> dict[str, Any]:
    all_items = walk_files(client)
    exact = [
        item for item in all_items
        if item.get("file_type") == 1 and (
            item.get("file_guid") == name_or_guid
            or (item.get("file_name") or "").strip() == name_or_guid.strip()
        )
    ]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ValueError(f"ambiguous mind name: {name_or_guid}")
    partial = [
        item for item in all_items
        if item.get("file_type") == 1 and name_or_guid.lower() in (item.get("file_name") or "").lower()
    ]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        names = ", ".join((item.get("file_name") or item.get("file_guid") or "") for item in partial[:5])
        raise ValueError(f"ambiguous mind name: {name_or_guid}; matches: {names}")
    raise ValueError(f"mind not found: {name_or_guid}")
