"""只读探查：薄封装 SeriesRelation list/describe。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.series_relation import SeriesRelation


def list_series_relations(arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    _ = arguments
    return SeriesRelation.list_user_series_relation_summaries()


def describe_series_relation(arguments: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(arguments, dict) or set(arguments) != {"key"}:
        return {"ok": False, "error": "只接受参数 key"}
    key = arguments.get("key")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}
    return SeriesRelation.describe_user_series_relation(key=key.strip())
