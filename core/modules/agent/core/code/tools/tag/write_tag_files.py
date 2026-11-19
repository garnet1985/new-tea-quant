"""write_tag_files：薄封装 Tag.apply_settings_patch。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.agent.core.code.conf.conf import (
    WRITE_TAG_ALLOWED_FIELDS,
    WRITE_TAG_MAX_CHARS,
)
from core.modules.agent.core.code.tools.tag._tag_key import parse_tag_key, tag_folder
from core.modules.tag import Tag


def _read_body(arguments: Dict[str, Any], name: str) -> str | Dict[str, Any]:
    body = arguments.get(name)
    if body is None:
        return ""
    if not isinstance(body, str) or not body.strip():
        return {"ok": False, "error": f"{name} 不能为空字符串"}
    if "\x00" in body:
        return {"ok": False, "error": f"{name} 含有无法写入的字符"}
    if len(body) > WRITE_TAG_MAX_CHARS:
        return {
            "ok": False,
            "error": f"{name} 超过 {WRITE_TAG_MAX_CHARS} 个字符",
        }
    return body


def write_tag_files(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """覆盖 tag.py / settings.py（至少写一个）。目录须已存在。"""
    if not isinstance(arguments, dict) or not set(arguments) <= WRITE_TAG_ALLOWED_FIELDS:
        return {
            "ok": False,
            "error": "只接受参数 key、tag_py、settings_py",
        }
    if "key" not in arguments:
        return {"ok": False, "error": "必须提供 key"}
    parsed = parse_tag_key({"key": arguments.get("key")}, only={"key"})
    if isinstance(parsed, dict):
        return parsed
    located = tag_folder(parsed)
    if isinstance(located, dict):
        return located

    tag_body = _read_body(arguments, "tag_py")
    if isinstance(tag_body, dict):
        return tag_body
    settings_body = _read_body(arguments, "settings_py")
    if isinstance(settings_body, dict):
        return settings_body
    if not tag_body and not settings_body:
        return {
            "ok": False,
            "error": "至少提供 tag_py、settings_py 之一",
        }

    out = Tag.apply_settings_patch(
        key=parsed,
        tag_py=tag_body,
        settings_py=settings_body,
    )
    if not out.get("ok"):
        err = str(out.get("error") or "写入失败")
        err = err.replace("scaffold_from_template", "create_tag")
        payload = {"ok": False, "error": err}
        if "key" in out:
            payload["key"] = out["key"]
        return payload

    return {
        "ok": True,
        "key": out.get("key") or parsed,
        "path": out.get("path") or located[1],
        "files": list(out.get("files") or []),
        "note": "文件已覆盖。接着调用 validate_tag，通过之前不要跑打标。",
    }
