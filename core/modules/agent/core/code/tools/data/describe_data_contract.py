"""describe_data_contract：薄封装 ContractIssuer.describe_user_contract。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.data_contract import ContractIssuer


def describe_data_contract(arguments: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(arguments, dict) or set(arguments) != {"data_key"}:
        return {"ok": False, "error": "只接受参数 data_key"}
    data_key = arguments.get("data_key")
    if not isinstance(data_key, str) or not data_key.strip():
        return {"ok": False, "error": "data_key 不能为空"}
    return ContractIssuer.describe_user_contract(data_key=data_key.strip())
