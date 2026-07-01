from __future__ import annotations

from typing import Any, Mapping

from core.modules.data_contract.core.registry.contract_const import ContractScope, DataKey

_CACHE_OVERRIDE_KEYS = frozenset({"cache", "use_cache", "enable_cache", "no_cache"})


def reject_per_entity_cache_overrides(
    data_id: DataKey,
    scope: ContractScope | None,
    override_params: Mapping[str, Any],
) -> None:
    if scope != ContractScope.PER_ENTITY or not override_params:
        return
    forbidden = [
        k for k in override_params if str(k).lower() in _CACHE_OVERRIDE_KEYS
    ]
    if not forbidden:
        return
    raise ValueError(
        f"PER_ENTITY 数据（{data_id.value}）不支持 cache：仅 GLOBAL 可缓存。"
        f"请查看 info({data_id.value}).has_cache；勿在 override_params 传入缓存相关参数。"
    )
