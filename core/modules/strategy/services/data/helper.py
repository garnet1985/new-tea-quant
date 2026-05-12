#!/usr/bin/env python3
"""Shared helpers for strategy data services."""

from __future__ import annotations

from typing import Any, Dict

from core.modules.data_contract.contract_const import DataKey
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)

_STORAGE_KEY_ALIASES = {
    DataKey.STOCK_KLINE: "klines",
    DataKey.TAG: "tags",
}


def storage_key_for(data_id: DataKey) -> str:
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


__all__ = ["storage_key_for", "normalize_declaration_item", "coerce_float"]
