#!/usr/bin/env python3
"""Data injection service."""

from __future__ import annotations

from typing import Any, Dict, List

from core.modules.data_contract.cache import ContractCacheManager
from core.modules.data_contract.contract_const import ContractScope, DataKey
from core.modules.data_contract.data_contract_manager import DataContractManager
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettings,
)
from core.modules.strategy.services.data.strategy_data_manager import StrategyDataManager


def preload_global_extras_for_enumeration(
    validated_settings: Dict[str, Any],
    start_date: str,
    end_date: str,
) -> Dict[str, List[Dict[str, Any]]]:
    ss = StrategySettings.from_dict(validated_settings)
    extras = ss.extra_required_data_sources
    if not extras:
        return {}

    dcm = DataContractManager(contract_cache=ContractCacheManager())
    out: Dict[str, List[Dict[str, Any]]] = {}

    for raw in extras:
        item = StrategySettings.normalize_extra_required_data_item(raw)
        dk = DataKey(str(item["data_id"]))
        spec = dcm.map.get(dk)
        if not spec or spec.get("scope") != ContractScope.GLOBAL:
            continue

        params = dict(item.get("params") or {})
        c = dcm.issue(dk, start=start_date, end=end_date, **params)
        slot = StrategyDataManager.storage_key_for(dk)
        out[slot] = list(c.data or [])
    return out

__all__ = ["preload_global_extras_for_enumeration"]
