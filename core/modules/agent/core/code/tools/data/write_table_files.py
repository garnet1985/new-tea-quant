"""write_table_files：薄封装 DataManager.write_user_table_files。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.agent.core.code.conf.conf import (
    WRITE_TABLE_ALLOWED_FIELDS,
    WRITE_TABLE_MAX_CHARS,
)
from core.modules.data_manager import DataManager


def write_table_files(arguments: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(arguments, dict) or not set(arguments) <= WRITE_TABLE_ALLOWED_FIELDS:
        return {"ok": False, "error": "只接受参数 key、schema_py、model_py"}
    if "key" not in arguments:
        return {"ok": False, "error": "必须提供 key"}
    key = arguments.get("key")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}

    schema_py = _body(arguments, "schema_py")
    if isinstance(schema_py, dict):
        return schema_py
    model_py = _body(arguments, "model_py")
    if isinstance(model_py, dict):
        return model_py
    return DataManager.write_user_table_files(
        key=key.strip(),
        schema_py=schema_py,
        model_py=model_py,
    )


def _body(arguments: Dict[str, Any], name: str) -> str | Dict[str, Any]:
    body = arguments.get(name)
    if body is None:
        return ""
    if not isinstance(body, str) or not body.strip():
        return {"ok": False, "error": f"{name} 不能为空字符串"}
    if "\x00" in body:
        return {"ok": False, "error": f"{name} 含有无法写入的字符"}
    if len(body) > WRITE_TABLE_MAX_CHARS:
        return {
            "ok": False,
            "error": f"{name} 超过 {WRITE_TABLE_MAX_CHARS} 个字符",
        }
    return body
