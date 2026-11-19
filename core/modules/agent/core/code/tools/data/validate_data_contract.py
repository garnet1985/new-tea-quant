"""validate_data_contract：薄封装 ContractIssuer.validate_user_contract。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.data_contract import ContractIssuer


def validate_data_contract(arguments: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(arguments, dict):
        return {"ok": False, "error": "参数须为对象"}
    allowed = {"key", "reload"}
    if not set(arguments) <= allowed or "key" not in arguments:
        return {"ok": False, "error": "只接受参数 key，可选 reload"}
    key = arguments.get("key")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}
    reload = arguments.get("reload", True)
    if not isinstance(reload, bool):
        return {"ok": False, "error": "reload 须为布尔"}
    return ContractIssuer.validate_user_contract(key=key.strip(), reload=reload)
