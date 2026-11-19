"""register_data_contract_key：薄封装 ContractIssuer.apply_user_data_key。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.data_contract import ContractIssuer


def register_data_contract_key(arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = dict(arguments or {})
    const_name = args.get("const_name")
    data_key = args.get("data_key")
    if not isinstance(const_name, str) or not const_name.strip():
        return {"ok": False, "error": "const_name 不能为空"}
    if not isinstance(data_key, str) or not data_key.strip():
        return {"ok": False, "error": "data_key 不能为空"}
    extra = set(args) - {"const_name", "data_key"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}
    return ContractIssuer.apply_user_data_key(
        const_name=const_name.strip(),
        data_key=data_key.strip(),
    )
