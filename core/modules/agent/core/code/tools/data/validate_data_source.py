"""validate_data_source：薄封装 DataSourceManager.validate_user_handler。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.data_source import DataSourceManager


def validate_data_source(arguments: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(arguments, dict) or set(arguments) != {"key"}:
        return {"ok": False, "error": "只接受参数 key"}
    key = arguments.get("key")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}
    return DataSourceManager.validate_user_handler(key=key.strip())
