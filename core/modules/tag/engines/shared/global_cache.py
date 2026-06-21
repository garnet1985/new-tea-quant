"""Scenario 级 GLOBAL 数据预加载。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.modules.data_contract.contract_const import ContractScope, DataKey
from core.modules.data_contract.data_contract_manager import DataContractManager


def build_global_extra_cache(
    settings: Dict[str, Any],
    *,
    dcm: DataContractManager,
    start: Optional[str],
    end: Optional[str],
) -> Dict[str, List[Dict[str, Any]]]:
    data_block = settings.get("data")
    if not isinstance(data_block, dict):
        return {}
    if not start or not end:
        return {}

    declarations = data_block.get("required") or []
    if not isinstance(declarations, list):
        return {}
    out: Dict[str, List[Dict[str, Any]]] = {}
    for item in declarations:
        data_id = str(item.get("data_id") or "").strip()
        if not data_id:
            continue
        dk = DataKey(data_id)
        spec = dcm.map.get(dk)
        if not spec:
            continue
        if spec.get("scope") != ContractScope.GLOBAL:
            continue
        params = dict(item.get("params") or {})
        c = dcm.issue(
            dk,
            start=start,
            end=end,
            **params,
        ).require_contract()
        out[dk.value] = list(c.data or [])
    return out
