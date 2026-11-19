"""create_tag：薄封装 Tag.scaffold_from_template。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.agent.core.code.tools.tag._tag_key import parse_tag_key, tag_folder
from core.modules.tag import Tag


def create_tag(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """新建标签场景。参数校验在信道；建目录与 meta.key 对齐在 Facade。"""
    parsed = parse_tag_key(arguments, only={"key"})
    if isinstance(parsed, dict):
        return parsed
    located = tag_folder(parsed)
    if isinstance(located, dict):
        return located
    _dest, relative = located
    out = Tag.scaffold_from_template(parsed)
    if not out.get("ok"):
        return {"ok": False, "error": _short_create_error(str(out.get("error") or ""), relative)}
    return {
        "ok": True,
        "key": out.get("key") or parsed,
        "path": out.get("path") or relative,
        "files": list(out.get("files") or ["tag.py", "settings.py"]),
        "note": str(out.get("note") or ""),
    }


def _short_create_error(message: str, relative: str) -> str:
    text = message.strip()
    if text.startswith("目标已存在"):
        return f"目标已存在: {relative}"
    if "模板目录不存在" in text or "标签模板不存在" in text:
        return "标签模板不存在: extensions/tags/_template/empty_scenario"
    return text
