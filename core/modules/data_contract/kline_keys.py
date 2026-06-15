"""Stock K-line DataKey helpers（供 contract / strategy / tag 共用）。"""
from __future__ import annotations

from typing import FrozenSet

from core.modules.data_contract.contract_const import DataKey

STOCK_KLINE_DATA_KEYS: FrozenSet[DataKey] = frozenset(
    {
        DataKey.STOCK_KLINE_DAILY,
        DataKey.STOCK_KLINE_WEEKLY,
        DataKey.STOCK_KLINE_MONTHLY,
    }
)

STOCK_KLINE_DATA_ID_VALUES: FrozenSet[str] = frozenset(
    dk.value for dk in STOCK_KLINE_DATA_KEYS
)

PRIMARY_KLINE_SLOT = "klines"


def is_stock_kline_data_key(data_id: DataKey) -> bool:
    return data_id in STOCK_KLINE_DATA_KEYS


def is_stock_kline_data_id_value(data_id: str) -> bool:
    return str(data_id or "").strip() in STOCK_KLINE_DATA_ID_VALUES


def kline_term_from_data_id_value(data_id: str) -> str:
    """从 ``stock.kline.{term}`` 解析周期名（daily / weekly / monthly）。"""
    value = str(data_id or "").strip()
    prefix = "stock.kline."
    if not value.startswith(prefix):
        raise ValueError(f"无法从 data_id 解析 K 线周期：{value!r}")
    term = value[len(prefix) :].strip()
    if term not in {"daily", "weekly", "monthly"}:
        raise ValueError(f"无法从 data_id 解析 K 线周期：{value!r}")
    return term


__all__ = [
    "PRIMARY_KLINE_SLOT",
    "STOCK_KLINE_DATA_KEYS",
    "STOCK_KLINE_DATA_ID_VALUES",
    "is_stock_kline_data_id_value",
    "is_stock_kline_data_key",
    "kline_term_from_data_id_value",
]
