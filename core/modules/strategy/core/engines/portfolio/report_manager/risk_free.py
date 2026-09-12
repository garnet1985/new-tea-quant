"""资金层无风险利率：隔夜 SHIBOR → 日利率。

表内 ``one_night`` 为年化百分数（与 Tushare / sys_shibor 一致）。
日利率 = pct / 100 / 252。缺日沿用最近已有；整段皆无则按 0。
不回退 LPR。
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Mapping, Optional, Sequence

from core.modules.strategy.core.engines.portfolio.report_manager.capital_metrics import (
    TRADING_DAYS_PER_YEAR,
)

logger = logging.getLogger(__name__)


def annual_pct_to_daily(annual_pct: float) -> float:
    """年化百分数 → 日利率。``1.5`` 表示 1.5%。"""
    try:
        pct = float(annual_pct)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(pct) or pct <= 0:
        return 0.0
    return pct / 100.0 / TRADING_DAYS_PER_YEAR


def fill_overnight_pct(
    dates: Sequence[str],
    annual_pct_by_date: Mapping[str, float],
) -> List[float]:
    """每个开市日的隔夜年化百分数；前后向填洞，全空则 0。"""
    mapped: Dict[str, float] = {}
    for raw_day, raw_pct in dict(annual_pct_by_date or {}).items():
        day = _norm_date(raw_day)
        pct = _positive_pct(raw_pct)
        if day and pct is not None:
            mapped[day] = pct
    filled: List[Optional[float]] = []
    last: Optional[float] = None
    for raw in dates:
        day = _norm_date(raw)
        if day in mapped:
            last = mapped[day]
        filled.append(last)
    first = next((x for x in filled if x is not None), None)
    return [float(first if x is None else x) if first is not None else 0.0 for x in filled]


def overnight_daily_rf(
    equity_dates: Sequence[str],
    annual_pct_by_date: Mapping[str, float],
) -> List[float]:
    """与日收益段对齐：第 i 段（date[i]→date[i+1]）用期末日的隔夜 SHIBOR。"""
    dates = [_norm_date(d) for d in equity_dates]
    if len(dates) < 2:
        return []
    pct = fill_overnight_pct(dates, annual_pct_by_date)
    return [annual_pct_to_daily(pct[i + 1]) for i in range(len(dates) - 1)]


def load_overnight_shibor(start_date: str = "", end_date: str = "") -> Dict[str, float]:
    """读 ``sys_shibor.one_night``。失败返回空 dict。"""
    start = _norm_date(start_date)
    end = _norm_date(end_date)
    try:
        from core.modules.data_manager import DataManager

        rows = DataManager().macro.load_shibor(start or None, end or None)
    except Exception:
        logger.warning("读 sys_shibor 失败，夏普按 rf=0", exc_info=True)
        return {}
    out: Dict[str, float] = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        day = _norm_date(row.get("date"))
        pct = _positive_pct(row.get("one_night"))
        if day and pct is not None:
            out[day] = pct
    if not out:
        logger.warning("sys_shibor 无隔夜数据 %s..%s，夏普按 rf=0", start, end)
    return out


def _norm_date(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text.replace("-", "").replace("/", "")[:8]


def _positive_pct(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out) or out <= 0:
        return None
    return out


__all__ = [
    "annual_pct_to_daily",
    "fill_overnight_pct",
    "overnight_daily_rf",
    "load_overnight_shibor",
]
