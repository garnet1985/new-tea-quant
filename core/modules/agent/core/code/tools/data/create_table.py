"""create_table：薄封装 DataManager.scaffold_user_table。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.data_manager import DataManager


def create_table(arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = dict(arguments or {})
    key = args.get("key")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}
    kind = args.get("kind", "data")
    table_name = args.get("table_name")
    if table_name is not None and not isinstance(table_name, str):
        return {"ok": False, "error": "table_name 须为字符串"}
    extra = set(args) - {"key", "kind", "table_name"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}
    return DataManager.scaffold_user_table(
        key=key.strip(),
        kind=str(kind or "data"),
        table_name=table_name.strip() if isinstance(table_name, str) else None,
    )
