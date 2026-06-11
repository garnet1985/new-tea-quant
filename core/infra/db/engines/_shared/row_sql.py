"""行数据 → SQL 片段、NaN 清洗、写入口标量规范（与具体 connector 无关）。"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence, Tuple

from core.infra.db.engines._shared.query_rows import normalize_query_row, normalize_query_rows


def normalize_write_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """写入口：Decimal/numpy → 原生标量（与读出口同一契约）。"""
    return normalize_query_row(row)


def normalize_write_rows(data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not data_list:
        return []
    return normalize_query_rows(data_list)


def rows_to_value_tuples(
    data_list: List[Dict[str, Any]], columns: Sequence[str]
) -> List[Tuple[Any, ...]]:
    normalized = normalize_write_rows(data_list)
    return [tuple(row[col] for col in columns) for row in normalized]


def to_columns_and_values(data_list: List[Dict[str, Any]]) -> tuple:
    """数据列表 → (列名列表, 占位符字符串)。"""
    if not data_list:
        return [], ""
    columns = list(data_list[0].keys())
    placeholders = ", ".join(["%s"] * len(columns))
    return columns, placeholders


def to_upsert_params(data_list: List[Dict[str, Any]], unique_keys: List[str]) -> tuple:
    """数据列表 → (columns, values, update_clause)。"""
    if not data_list:
        return [], [], ""

    columns = list(data_list[0].keys())
    missing_keys = [k for k in unique_keys if k not in columns]
    if missing_keys:
        raise ValueError(f"主键字段在数据中缺失: {missing_keys}")

    update_fields = [k for k in columns if k not in unique_keys]
    update_clause = (
        ", ".join([f"{k} = EXCLUDED.{k}" for k in update_fields]) if update_fields else ""
    )
    values = rows_to_value_tuples(data_list, columns)
    return columns, values, update_clause


def clean_nan_value(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    try:
        if isinstance(value, float) and math.isnan(value):
            return default
    except (TypeError, ValueError):
        pass
    try:
        import pandas as pd

        if pd.isna(value):
            return default
    except (ImportError, AttributeError, TypeError):
        pass
    return value


def clean_nan_in_dict(data: Dict[str, Any], default: Any = None) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return data
    return {key: clean_nan_value(value, default=default) for key, value in data.items()}


def clean_nan_in_list(
    data_list: List[Dict[str, Any]], default: Any = None
) -> List[Dict[str, Any]]:
    if not isinstance(data_list, list):
        return data_list
    return [clean_nan_in_dict(item, default=default) for item in data_list]
