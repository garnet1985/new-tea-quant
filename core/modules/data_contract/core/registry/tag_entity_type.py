"""Tag ``target_entity.type`` 与 ``DataKey`` 的映射（写入 sys_tag_value.entity_type）。"""
from __future__ import annotations

from typing import Dict

from core.modules.data_contract.core.registry.contract_const import ContractScope, DataKey
from core.modules.data_contract.core.registry.kline_keys import is_stock_kline_data_key, kline_term_from_data_id_value
from core.modules.data_contract.core.registry.mapping import default_map

# 非 K 线类 PER_ENTITY 时序源 → tag 存储维度 entity_type
_TAG_ENTITY_TYPE_BY_DATA_KEY: Dict[DataKey, str] = {
    DataKey.STOCK_CORPORATE_FINANCE: "corporate_finance",
    DataKey.STOCK_INDICATORS_DAILY: "stock_kline_daily",
    DataKey.STOCK_MONEYFLOW_DAILY: "stock_kline_daily",
    DataKey.STOCK_ADJ_FACTOR_EVENTS: "stock_kline_daily",
    DataKey.TAG: "tag_scenario",
    DataKey.INDEX_KLINE_DAILY: "index_kline_daily",
    DataKey.INDEX_WEIGHT_DAILY: "index_kline_daily",
}


def resolve_tag_entity_type(data_id: DataKey | str) -> str:
    """
    由 ``data.base_required_data.data_id`` 推导 Tag 作业的 ``target_entity.type``。

    股票 K 线：``stock_kline_{daily|weekly|monthly}``；其余见上表或 PER_ENTITY 兜底。
    """
    dk = data_id if isinstance(data_id, DataKey) else DataKey(str(data_id).strip())
    if is_stock_kline_data_key(dk):
        term = kline_term_from_data_id_value(dk.value)
        return f"stock_kline_{term}"
    mapped = _TAG_ENTITY_TYPE_BY_DATA_KEY.get(dk)
    if mapped:
        return mapped
    spec = default_map.get(dk)
    if spec and spec.get("scope") == ContractScope.PER_ENTITY:
        return dk.value.replace(".", "_")
    raise ValueError(
        f"data_id={dk.value!r} 无法推导 tag target_entity.type；"
        "请使用 PER_ENTITY + TIME_SERIES 的 DataKey 作为 base"
    )


__all__ = ["resolve_tag_entity_type"]
