"""slice_based 换仓周期辅助（devtools 演示策略共用）。"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Union

CalendarLike = Union[Mapping[str, Any], Any]


def _calendar_get(calendar: CalendarLike, key: str, default: Any = None) -> Any:
    if isinstance(calendar, dict):
        return calendar.get(key, default)
    return getattr(calendar, key, default)


def require_rebalance_period(settings: Dict[str, Any]) -> str:
    core = settings.get("core") or {}
    period = str(core.get("rebalance_period") or "").strip()
    if not period:
        raise ValueError("core.rebalance_period 必填（例如 year / month）")
    return period


def is_rebalance_period_start(calendar: CalendarLike, period: str) -> bool:
    """周期首个决策日；优先读 calendar.is_period_start（slice worker 注入）。"""
    _ = period
    explicit = _calendar_get(calendar, "is_period_start")
    if explicit is not None:
        return bool(explicit)
    flags = _calendar_get(calendar, "flags") or {}
    if isinstance(flags, dict) and "period_start" in flags:
        return bool(flags["period_start"])
    return False


def is_rebalance_period_end(calendar: CalendarLike, period: str) -> bool:
    """周期末个决策日；优先读 calendar.is_period_end（slice worker 注入）。"""
    _ = period
    explicit = _calendar_get(calendar, "is_period_end")
    if explicit is not None:
        return bool(explicit)
    flags = _calendar_get(calendar, "flags") or {}
    if isinstance(flags, dict) and "period_end" in flags:
        return bool(flags["period_end"])
    return False
