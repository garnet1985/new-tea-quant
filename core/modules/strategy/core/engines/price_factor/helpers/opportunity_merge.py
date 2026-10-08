"""价格回放：base 轴间隔与默认是否开新段。

本文件:
- opportunity_axis_gap / is_new_by_merge_gap / axis_from_klines
  边界: 只算间隔；不负责成交、涨跌停或钩子组装
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from core.infra.utils import Utils

from core.modules.strategy.core.engines.shared.services.strategy_settings.simulation_settings.price import (
    DEFAULT_OPPORTUNITY_MERGE_GAP,
)


def axis_from_klines(klines: Sequence[Dict[str, Any]]) -> List[str]:
    """K 线 ``date`` 去重保序，作 base 轴。"""
    out: List[str] = []
    seen = set()
    for row in klines or ():
        if not isinstance(row, dict):
            continue
        stamp = str(row.get("date") or "").strip()
        if not stamp or stamp in seen:
            continue
        seen.add(stamp)
        out.append(stamp)
    return out


def opportunity_axis_gap(
    previous: str,
    current: str,
    axis: Sequence[str],
) -> Optional[int]:
    """current 相对 previous 的 base 步数；相邻为 1。算不出返回 None。"""
    prev = str(previous or "").strip()
    curr = str(current or "").strip()
    if not prev or not curr:
        return None
    if prev == curr:
        return 0
    index = {stamp: i for i, stamp in enumerate(axis) if str(stamp or "").strip()}
    if prev in index and curr in index:
        return max(0, int(index[curr]) - int(index[prev]))
    try:
        return max(0, int(Utils.date.diff_days(prev, curr)))
    except (TypeError, ValueError):
        return None


def is_new_by_merge_gap(
    *,
    previous_exists: bool,
    gap: Optional[int],
    merge_gap: int = DEFAULT_OPPORTUNITY_MERGE_GAP,
) -> bool:
    """默认：无上一笔或 gap 未知则开新段；gap > merge_gap 才算新段。"""
    if not previous_exists:
        return True
    if gap is None:
        return True
    try:
        limit = int(merge_gap)
    except (TypeError, ValueError):
        limit = DEFAULT_OPPORTUNITY_MERGE_GAP
    return int(gap) > limit


def trigger_stamp(row: Any) -> str:
    """合并比较用的时间戳：trigger_date，否则 entry_date。"""
    trigger = str(getattr(row, "trigger_date", "") or "").strip()
    if trigger:
        return trigger
    return str(getattr(row, "entry_date", "") or "").strip()


__all__ = [
    "axis_from_klines",
    "is_new_by_merge_gap",
    "opportunity_axis_gap",
    "trigger_stamp",
]
