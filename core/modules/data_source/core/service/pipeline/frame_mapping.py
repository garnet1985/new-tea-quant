"""列名映射：DataFrame 进，DataFrame 出。写库时再按行切成记录。"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

import pandas as pd

WRITE_CHUNK_ROWS = 2000
_TEXT_FILL_FIELDS = {"date", "quarter", "month"}


def frame_nbytes(frame: pd.DataFrame) -> int:
    if frame is None or frame.empty:
        return 0
    return int(frame.memory_usage(deep=True).sum())


def mapping_is_columns(mapping: Optional[Mapping[str, Any]]) -> bool:
    if not mapping:
        return False
    return all(isinstance(source, str) for source in mapping.values())


def map_columns(
    frame: pd.DataFrame,
    mapping: Mapping[str, Any],
    *,
    constants: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """按目标列名选取、改名，并写入常量列。缺列按字段类型填 0 或空字符串。"""
    columns: Dict[str, Any] = {}
    for target, source in mapping.items():
        if not isinstance(source, str):
            raise TypeError(f"map_columns 只接受列名映射，收到 {type(source)}")
        if source in frame.columns:
            series = frame[source]
            if pd.api.types.is_numeric_dtype(series):
                columns[target] = pd.to_numeric(series, errors="coerce").astype("float64")
            else:
                columns[target] = series.to_numpy()
        elif target in _TEXT_FILL_FIELDS:
            columns[target] = ""
        else:
            columns[target] = 0.0
    mapped = pd.DataFrame(columns, index=range(len(frame)))
    for name, value in (constants or {}).items():
        mapped[name] = value
    return mapped


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (str, bytes, bool, int)):
        return False
    try:
        flag = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(flag) if isinstance(flag, bool) else False


def records_from_frame(frame: pd.DataFrame) -> List[Dict[str, Any]]:
    if frame is None or frame.empty:
        return []
    rows: List[Dict[str, Any]] = []
    for raw in frame.to_dict("records"):
        item: Dict[str, Any] = {}
        for key, value in raw.items():
            item[key] = None if _is_missing(value) else value
        rows.append(item)
    return rows


def iter_record_chunks(frame: pd.DataFrame, chunk_rows: int = WRITE_CHUNK_ROWS):
    """按行切出记录。一次只展开一块，避免整表再变一份字典。"""
    if frame is None or frame.empty:
        return
    step = max(1, int(chunk_rows))
    total = len(frame)
    for start in range(0, total, step):
        rows = records_from_frame(frame.iloc[start : start + step])
        if rows:
            yield rows
