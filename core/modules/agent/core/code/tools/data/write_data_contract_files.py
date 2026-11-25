"""write_data_contract_files：薄封装 ContractIssuer.write_user_contract_files。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.agent.core.code.conf.conf import (
    WRITE_DATA_CONTRACT_ALLOWED_FIELDS,
    WRITE_DATA_CONTRACT_MAX_CHARS,
)
from core.modules.data_contract import ContractIssuer


def write_data_contract_files(arguments: Dict[str, Any]) -> Dict[str, Any]:
    if (
        not isinstance(arguments, dict)
        or not set(arguments) <= WRITE_DATA_CONTRACT_ALLOWED_FIELDS
    ):
        return {
            "ok": False,
            "error": "只接受参数 key、declaration_py、loader_py、contract_py",
        }
    if "key" not in arguments:
        return {"ok": False, "error": "必须提供 key"}
    key = arguments.get("key")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}

    declaration_py = _body(arguments, "declaration_py")
    if isinstance(declaration_py, dict):
        return declaration_py
    loader_py = _body(arguments, "loader_py")
    if isinstance(loader_py, dict):
        return loader_py
    contract_py = _body(arguments, "contract_py")
    if isinstance(contract_py, dict):
        return contract_py
    return ContractIssuer.write_user_contract_files(
        key=key.strip(),
        declaration_py=declaration_py,
        loader_py=loader_py,
        contract_py=contract_py,
    )


def _body(arguments: Dict[str, Any], name: str) -> str | Dict[str, Any]:
    body = arguments.get(name)
    if body is None:
        return ""
    if not isinstance(body, str) or not body.strip():
        return {"ok": False, "error": f"{name} 不能为空字符串"}
    if "\x00" in body:
        return {"ok": False, "error": f"{name} 含有无法写入的字符"}
    if len(body) > WRITE_DATA_CONTRACT_MAX_CHARS:
        return {
            "ok": False,
            "error": f"{name} 超过 {WRITE_DATA_CONTRACT_MAX_CHARS} 个字符",
        }
    return body
