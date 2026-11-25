"""validate_series_relation：薄封装 SeriesRelation.validate_user_series_relation。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.series_relation import SeriesRelation


def validate_series_relation(arguments: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(arguments, dict) or set(arguments) != {"key"}:
        return {"ok": False, "error": "只接受参数 key"}
    key = arguments.get("key")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}
    return SeriesRelation.validate_user_series_relation(key=key.strip())
