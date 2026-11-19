"""create_data_contract：薄封装 ContractIssuer.scaffold_user_contract。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.data_contract import ContractIssuer


def create_data_contract(arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = dict(arguments or {})
    key = args.get("key")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}

    allowed = {
        "key",
        "data_key",
        "const_name",
        "contract_type",
        "scope",
        "list_data_key",
        "display_name",
    }
    extra = set(args) - allowed
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}

    def _opt_str(name: str) -> str | None | Dict[str, Any]:
        if name not in args or args[name] is None:
            return None
        val = args[name]
        if not isinstance(val, str):
            return {"ok": False, "error": f"{name} 须为字符串"}
        text = val.strip()
        return text or None

    data_key = _opt_str("data_key")
    if isinstance(data_key, dict):
        return data_key
    const_name = _opt_str("const_name")
    if isinstance(const_name, dict):
        return const_name
    contract_type = args.get("contract_type", "non_time_series")
    if not isinstance(contract_type, str):
        return {"ok": False, "error": "contract_type 须为字符串"}
    scope = args.get("scope", "global")
    if not isinstance(scope, str):
        return {"ok": False, "error": "scope 须为字符串"}
    list_data_key = args.get("list_data_key", "")
    if list_data_key is None:
        list_data_key = ""
    if not isinstance(list_data_key, str):
        return {"ok": False, "error": "list_data_key 须为字符串"}
    display_name = args.get("display_name", "")
    if display_name is None:
        display_name = ""
    if not isinstance(display_name, str):
        return {"ok": False, "error": "display_name 须为字符串"}

    return ContractIssuer.scaffold_user_contract(
        key=key.strip(),
        data_key=data_key,
        const_name=const_name,
        contract_type=contract_type.strip() or "non_time_series",
        scope=scope.strip() or "global",
        list_data_key=list_data_key.strip(),
        display_name=display_name.strip(),
    )
