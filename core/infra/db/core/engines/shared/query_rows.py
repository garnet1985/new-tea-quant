"""
查询结果行规范化 — 所有 backend 读出口的单一契约。

框架数值契约（窄接口，业务层不得再兼容 Decimal/numpy）：

读（connector 出口）：
- DECIMAL/NUMERIC → float
- numpy 标量 → 原生 int/float/bool
- float NaN → None

写（row_sql / BatchOperation 入口）：
- 同上规范化后再格式化为 SQL 字面量或参数绑定

业务层只允许 float/int 参与计算；若从 DB 读到 Decimal 说明读出口失败。
写入时若仍出现 Decimal，写入口会转为 float 再落库（业务层不应依赖此兜底）。
"""
from __future__ import annotations

import math
from decimal import Decimal
from typing import Any, Dict, List, Sequence


def _is_numpy_scalar(value: Any) -> bool:
    mod = getattr(type(value), "__module__", "") or ""
    return mod == "numpy" or mod.startswith("numpy.")


def normalize_cell_value(value: Any) -> Any:
    """将驱动/中间层标量规范为框架内可安全计算的类型。"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        f = float(value)
        return None if math.isnan(f) else f
    if _is_numpy_scalar(value):
        if hasattr(value, "item"):
            return normalize_cell_value(value.item())
        return value
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def normalize_query_row(row: Dict[str, Any]) -> Dict[str, Any]:
    if not row:
        return row
    return {key: normalize_cell_value(val) for key, val in row.items()}


def normalize_query_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not rows:
        return []
    return [normalize_query_row(row) for row in rows]


def tuples_to_dicts(columns: Sequence[str], rows: Sequence[Sequence[Any]]) -> List[Dict[str, Any]]:
    """列名 + 元组行 → dict 行（未做标量规范化）。"""
    if not columns or not rows:
        return []
    cols = list(columns)
    return [dict(zip(cols, row)) for row in rows]


def fetch_result_to_rows(result: Any) -> List[Dict[str, Any]]:
    """
    将 DB-API / DuckDB execute 返回值转为 dict 行列表（无 pandas）。

    支持：
    - DuckDBPyRelation（.columns + .fetchall）
    - DuckDBPyConnection 链式 execute 后（.description + .fetchall）
    """
    if result is None:
        return []
    fetchall = getattr(result, "fetchall", None)
    if not callable(fetchall):
        return []
    rows = fetchall()
    if not rows:
        return []
    columns = list(getattr(result, "columns", None) or [])
    if not columns:
        description = getattr(result, "description", None) or []
        columns = [str(col[0]) for col in description if col]
    if not columns:
        return []
    return tuples_to_dicts(columns, rows)


def fetch_result_to_normalized_rows(result: Any) -> List[Dict[str, Any]]:
    """fetch_result_to_rows + normalize_query_rows。"""
    return normalize_query_rows(fetch_result_to_rows(result))
