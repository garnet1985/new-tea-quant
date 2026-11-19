"""create_data_source：薄封装 DataSourceManager.scaffold_user_handler。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.data_source import DataSourceManager


def create_data_source(arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = dict(arguments or {})
    key = args.get("key")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}
    hooks = args.get("hooks_class_name")
    if hooks is not None and not isinstance(hooks, str):
        return {"ok": False, "error": "hooks_class_name 须为字符串"}
    extra = set(args) - {"key", "hooks_class_name"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}
    return DataSourceManager.scaffold_user_handler(
        key=key.strip(),
        hooks_class_name=hooks.strip() if isinstance(hooks, str) and hooks.strip() else None,
    )
