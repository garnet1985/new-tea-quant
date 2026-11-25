"""Markdown YAML frontmatter（templates 命中条件）。"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from core.infra.discovery import Discovery


def split_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """返回 (meta, body)。无 ``---`` 头则 meta 为空。"""
    raw = str(text or "")
    if not raw.startswith("---"):
        return {}, raw
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, raw
    end = -1
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end < 0:
        return {}, raw
    meta_text = "\n".join(lines[1:end]).strip()
    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    if not meta_text:
        return {}, body
    parsed = Discovery.file.parse_yaml_text(meta_text)
    if not isinstance(parsed, dict):
        return {}, body if parsed is None else raw
    return parsed, body
