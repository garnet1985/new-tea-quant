"""register_data_source：薄封装 DataSourceManager.apply_mapping_entry。"""

from __future__ import annotations

from typing import Any, Dict, List

from core.modules.data_source import DataSourceManager


def register_data_source(arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = dict(arguments or {})
    key = args.get("key")
    handler = args.get("handler")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}
    if not isinstance(handler, str) or not handler.strip():
        return {"ok": False, "error": "handler 不能为空"}

    is_enabled = args.get("is_enabled", True)
    if not isinstance(is_enabled, bool):
        return {"ok": False, "error": "is_enabled 须为布尔"}

    depends_on = args.get("depends_on")
    deps: List[str] | None = None
    if depends_on is not None:
        if not isinstance(depends_on, list) or not all(
            isinstance(x, str) for x in depends_on
        ):
            return {"ok": False, "error": "depends_on 须为字符串列表"}
        deps = depends_on

    weight = args.get("weight")
    if weight is not None and not isinstance(weight, int):
        return {"ok": False, "error": "weight 须为整数"}

    extra = set(args) - {"key", "handler", "is_enabled", "depends_on", "weight"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}

    return DataSourceManager.apply_mapping_entry(
        key=key.strip(),
        handler=handler.strip(),
        is_enabled=is_enabled,
        depends_on=deps,
        weight=weight,
    )
