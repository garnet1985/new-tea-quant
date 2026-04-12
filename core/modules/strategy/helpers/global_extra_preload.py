"""
主进程预加载 ``extra_required_data_sources`` 中 ``ContractScope.GLOBAL`` 的数据（MVP：opt1，随 job pickle 到子进程）。
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.modules.data_contract.cache import ContractCacheManager
from core.modules.data_contract.contract_const import ContractScope, DataKey
from core.modules.data_contract.data_contract_manager import DataContractManager
from core.modules.strategy.models.strategy_settings import StrategySettings


def _storage_key_for_data_id(data_id: DataKey) -> str:
    """与 ``StrategyWorkerDataManager._storage_key_for`` 保持一致（避免 helpers ↔ SWM 循环依赖）。"""
    if data_id == DataKey.STOCK_KLINE:
        return "klines"
    if data_id == DataKey.TAG:
        return "tags"
    return data_id.value


def preload_global_extras_for_enumeration(
    validated_settings: Dict[str, Any],
    start_date: str,
    end_date: str,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    在主进程为枚举任务加载所有 GLOBAL 的 extra 依赖，返回 ``{存储槽位: rows}``。

    PER_ENTITY 的 extra 不在此加载，由子进程自行拉取。
    """
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
        slot = _storage_key_for_data_id(dk)
        out[slot] = list(c.data or [])

    return out
