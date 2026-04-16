#!/usr/bin/env python3
"""根据 data contract mapping 判断缓存落在 global 还是 per-run（缓存 scope）。

仅 **ContractScope.GLOBAL** 下的非时序 / 时序会进入两层缓存；``PER_ENTITY`` 等其余情况一律
``NONE``（走 loader，不进本组件缓存）。见 ``resolve_cache_scope``。
"""

from __future__ import annotations

from ..contract_const import ContractScope, ContractType, DataKey
from ..mapping import DataSpec, DataSpecMap

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
