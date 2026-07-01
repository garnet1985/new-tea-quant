#!/usr/bin/env python3
"""Shared helpers for strategy data services."""

from __future__ import annotations

from typing import Any, Dict

from core.modules.data_contract.contracts import DataKey
from core.modules.data_contract.core.registry.kline_keys import (
    PRIMARY_KLINE_SLOT,
    is_stock_kline_data_key,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)

_STORAGE_KEY_ALIASES = {
    DataKey.TAG: "tags",
}


def storage_key_for(data_id: DataKey, *, is_base: bool = False) -> str:
    """base 的 K 线 → 主 slot ``klines``；其余数据源 slot 默认为 ``data_id``。"""
    if is_base and is_stock_kline_data_key(data_id):
        return PRIMARY_KLINE_SLOT
    return _STORAGE_KEY_ALIASES.get(data_id, data_id.value)


def normalize_declaration_item(
    settings: StrategySettingsView,
    raw: Dict[str, Any],
) -> Dict[str, Any]:
    item = dict(raw)
    dk = DataKey(str(item["data_id"]))
    params = dict(item.get("params") or {})
    if dk == DataKey.TAG and str(params.get("entity_type") or "").strip() == "":
        et = settings.tag_storage_entity_type
        if et:
            params["entity_type"] = str(et)
        item["params"] = params
    return item


def coerce_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (ValueError, TypeError):
        return 0.0


__all__ = [
    "coerce_float",
    "normalize_declaration_item",
    "storage_key_for",
]
