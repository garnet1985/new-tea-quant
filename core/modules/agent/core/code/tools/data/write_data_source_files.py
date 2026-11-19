"""write_data_source_files：薄封装 DataSourceManager.write_user_handler_files。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.agent.core.code.conf.conf import (
    WRITE_DATA_SOURCE_ALLOWED_FIELDS,
    WRITE_DATA_SOURCE_MAX_CHARS,
)
from core.modules.data_source import DataSourceManager


def write_data_source_files(arguments: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(arguments, dict) or not set(arguments) <= WRITE_DATA_SOURCE_ALLOWED_FIELDS:
        return {"ok": False, "error": "只接受参数 key、handler_py、settings_py"}
    if "key" not in arguments:
        return {"ok": False, "error": "必须提供 key"}
    key = arguments.get("key")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}

    handler_py = _body(arguments, "handler_py")
    if isinstance(handler_py, dict):
        return handler_py
    settings_py = _body(arguments, "settings_py")
    if isinstance(settings_py, dict):
        return settings_py
    return DataSourceManager.write_user_handler_files(
        key=key.strip(),
        handler_py=handler_py,
        settings_py=settings_py,
    )


def _body(arguments: Dict[str, Any], name: str) -> str | Dict[str, Any]:
    body = arguments.get(name)
    if body is None:
        return ""
    if not isinstance(body, str) or not body.strip():
        return {"ok": False, "error": f"{name} 不能为空字符串"}
    if "\x00" in body:
        return {"ok": False, "error": f"{name} 含有无法写入的字符"}
    if len(body) > WRITE_DATA_SOURCE_MAX_CHARS:
        return {
            "ok": False,
            "error": f"{name} 超过 {WRITE_DATA_SOURCE_MAX_CHARS} 个字符",
        }
    return body
