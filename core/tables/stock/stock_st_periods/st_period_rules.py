"""
ST / *ST 简称解析与时段判定（与数据源无关，供 core 与 handler 共用）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.utils.date.date_utils import DateUtils

ST_LEVEL_STAR_ST = "STAR_ST"
ST_LEVEL_S_STAR_ST = "S_STAR_ST"
ST_LEVEL_SST = "SST"
ST_LEVEL_ST = "ST"

ALL_ST_LEVELS = (
    ST_LEVEL_STAR_ST,
    ST_LEVEL_S_STAR_ST,
    ST_LEVEL_SST,
    ST_LEVEL_ST,
)


def classify_st_level(name: str) -> Optional[str]:
    raw = (name or "").strip()
    if not raw:
        return None
    if raw.startswith("*ST"):
        return ST_LEVEL_STAR_ST
    if raw.startswith("S*ST"):
        return ST_LEVEL_S_STAR_ST
    if raw.startswith("SST"):
        return ST_LEVEL_SST
    if raw.startswith("ST"):
        return ST_LEVEL_ST
    return None


def normalize_yyyymmdd(value: Any) -> str:
    text = str(value or "").strip().replace("-", "")
    return text if len(text) == 8 and text.isdigit() else ""


def is_active_on(
    period: Dict[str, Any],
    trade_date: str,
    *,
    levels: Optional[Sequence[str]] = None,
) -> bool:
    d = normalize_yyyymmdd(trade_date)
    if not d:
        return False
    level = str(period.get("st_level") or "")
    if levels is not None and level not in levels:
        return False
    start = normalize_yyyymmdd(period.get("start_date"))
    if not start or d < start:
        return False
    end = normalize_yyyymmdd(period.get("end_date"))
    if end and d > end:
        return False
    return True


def records_to_st_periods(
    records: List[Dict[str, Any]],
    *,
    stock_id: str,
    source: str = "namechange",
    last_update: str = "",
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    sid = str(stock_id or "").strip()
    if not sid:
        return out

    for row in records:
        name = str(row.get("name") or "")
        level = classify_st_level(name)
        if not level:
            continue
        start = normalize_yyyymmdd(row.get("start_date"))
        if not start:
            continue
        end = normalize_yyyymmdd(row.get("end_date")) or None
        ann = normalize_yyyymmdd(row.get("ann_date")) or None
        reason = str(row.get("change_reason") or "").strip() or None
        out.append(
            {
                "stock_id": sid,
                "st_level": level,
                "start_date": start,
                "end_date": end,
                "name_snapshot": name[:64],
                "change_reason": reason,
                "ann_date": ann,
                "source": source,
                "last_update": last_update,
            }
        )
    return consolidate_st_periods(out)


def consolidate_st_periods(periods: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    去重主键、按 start_date 排序，并将未闭合的 end_date 截断到下一段 start 的前一日，
    避免 namechange 多行导致的时段重叠（尤其 end_date 为空时）。
    """
    if not periods:
        return []

    by_pk: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for row in periods:
        sid = str(row.get("stock_id") or "").strip()
        level = str(row.get("st_level") or "").strip()
        start = normalize_yyyymmdd(row.get("start_date"))
        if not sid or not level or not start:
            continue
        by_pk[(sid, level, start)] = dict(row)

    ordered = sorted(
        by_pk.values(),
        key=lambda p: (normalize_yyyymmdd(p.get("start_date")), str(p.get("st_level") or "")),
    )

    for i, period in enumerate(ordered):
        start = normalize_yyyymmdd(period.get("start_date"))
        end = normalize_yyyymmdd(period.get("end_date")) or None
        if i + 1 < len(ordered):
            next_start = normalize_yyyymmdd(ordered[i + 1].get("start_date"))
            if next_start and start and next_start > start:
                if not end or end >= next_start:
                    period["end_date"] = DateUtils.sub_days(next_start, 1)
        elif not end:
            period["end_date"] = None
        else:
            period["end_date"] = end

    return ordered
