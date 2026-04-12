#!/usr/bin/env python3
"""根据 data contract mapping 判断缓存落在 global 还是 per-strategy（缓存 scope）。"""

from __future__ import annotations

from core.modules.data_contract.contract_const import ContractScope, ContractType, DataKey
from core.modules.data_contract.mapping import DataSpec, DataSpecMap

from .contract_cache_scope import ContractCacheScope


def resolve_cache_scope(spec: DataSpec) -> ContractCacheScope:
    ds = spec.get("scope")
    ctype = spec.get("type")
    if ds == ContractScope.GLOBAL and ctype == ContractType.NON_TIME_SERIES:
        return ContractCacheScope.GLOBAL
    if ds == ContractScope.GLOBAL and ctype == ContractType.TIME_SERIES:
        return ContractCacheScope.PER_STRATEGY
    return ContractCacheScope.NONE


def resolve_cache_scope_for_data_key(dcm_map: DataSpecMap, data_id: DataKey) -> ContractCacheScope:
    spec = dcm_map.get(data_id)
    if not spec:
        return ContractCacheScope.NONE
    return resolve_cache_scope(spec)
