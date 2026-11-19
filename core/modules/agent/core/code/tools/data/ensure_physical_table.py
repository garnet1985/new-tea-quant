"""ensure_physical_table：薄封装 DataManager.ensure_user_table。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.data_manager import DataManager


def ensure_physical_table(arguments: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(arguments, dict) or set(arguments) != {"key"}:
        return {"ok": False, "error": "只接受参数 key"}
    key = arguments.get("key")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}
    return DataManager().ensure_user_table(key=key.strip())
