"""write_series_relation_settings：薄封装 SeriesRelation.write_user_series_relation_settings。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.agent.core.code.conf.conf import (
    WRITE_SERIES_RELATION_ALLOWED_FIELDS,
    WRITE_SERIES_RELATION_MAX_CHARS,
)
from core.modules.series_relation import SeriesRelation


def write_series_relation_settings(arguments: Dict[str, Any]) -> Dict[str, Any]:
    if (
        not isinstance(arguments, dict)
        or not set(arguments) <= WRITE_SERIES_RELATION_ALLOWED_FIELDS
    ):
        return {"ok": False, "error": "只接受参数 key、settings_py"}
    if "key" not in arguments:
        return {"ok": False, "error": "必须提供 key"}
    key = arguments.get("key")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}
    body = arguments.get("settings_py")
    if not isinstance(body, str) or not body.strip():
        return {"ok": False, "error": "settings_py 不能为空"}
    if "\x00" in body:
        return {"ok": False, "error": "settings_py 含有无法写入的字符"}
    if len(body) > WRITE_SERIES_RELATION_MAX_CHARS:
        return {
            "ok": False,
            "error": f"settings_py 超过 {WRITE_SERIES_RELATION_MAX_CHARS} 个字符",
        }
    return SeriesRelation.write_user_series_relation_settings(
        key=key.strip(),
        settings_py=body,
    )
