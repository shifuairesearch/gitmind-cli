from __future__ import annotations

import re
from typing import Any


BULLET_RE = re.compile(r"^(\s*)[-*+]\s+(.*)$")
HEADING_RE = re.compile(r"^#\s+(.+?)\s*$")


def make_node(text: str) -> dict[str, Any]:
    return {"data": {"text": text.strip()}, "children": []}


def parse_markdown_outline(markdown: str) -> dict[str, Any]:
    root = make_node("Untitled")
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    last_node: dict[str, Any] | None = None
    saw_heading = False

    for raw_line in markdown.splitlines():
        if not raw_line.strip():
            continue
        heading = HEADING_RE.match(raw_line)
        if heading and not saw_heading:
            root["data"]["text"] = heading.group(1).strip()
            saw_heading = True
            last_node = root
            continue
        bullet = BULLET_RE.match(raw_line)
        if bullet:
            indent = len(bullet.group(1).replace("\t", "    "))
            text = bullet.group(2).strip()
            node = make_node(text)
            while stack and stack[-1][0] >= indent:
                stack.pop()
            parent = stack[-1][1] if stack else root
            parent.setdefault("children", []).append(node)
            stack.append((indent, node))
            last_node = node
            continue
        if last_node is not None:
            current = last_node.setdefault("data", {}).get("text", "")
            last_node["data"]["text"] = f"{current}\n{raw_line.strip()}".strip()

    return normalize_content({"root": root})


def normalize_content(content: dict[str, Any]) -> dict[str, Any]:
    content.setdefault("root", make_node("Untitled"))
    content.setdefault("style", {"theme": {"colorTheme": "default", "structTheme": "right"}})
    content.setdefault("relLines", [])
    content.setdefault("floatRoots", [])
    return content
