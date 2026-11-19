"""create_series_relation：薄封装 SeriesRelation.scaffold_user_series_relation。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.series_relation import SeriesRelation


def create_series_relation(arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = dict(arguments or {})
    key = args.get("key")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}
    display_name = args.get("display_name", "")
    if display_name is None:
        display_name = ""
    if not isinstance(display_name, str):
        return {"ok": False, "error": "display_name 须为字符串"}
    extra = set(args) - {"key", "display_name"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}
    return SeriesRelation.scaffold_user_series_relation(
        key=key.strip(),
        display_name=display_name.strip(),
    )
