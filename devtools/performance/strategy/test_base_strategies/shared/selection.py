"""slice_based 横截面选股辅助（devtools 演示策略共用）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional

INDICATORS = "indicators"
TAGS_SLOT = "tags"


@dataclass(frozen=True)
class RebalanceFilters:
    min_close: float
    max_close: float
    top_n: int
    cap_filter: str

    @classmethod
    def from_settings(cls, settings: Dict[str, Any]) -> RebalanceFilters:
        core = settings.get("core") or {}
        return cls(
            min_close=float(core.get("min_close", 0.0)),
            max_close=float(core.get("max_close", 1e9)),
            top_n=max(1, int(core.get("top_n", 20))),
            cap_filter=str(core.get("cap_filter") or "none").strip().lower(),
        )


def find_bar_on_date(
    klines: Iterable[Mapping[str, Any]],
    as_of_date: str,
) -> Optional[Dict[str, Any]]:
    target = str(as_of_date or "").strip()
    if not target:
        return None
    for row in klines:
        if str(row.get("date") or "") == target:
            return dict(row)
    return None


def passes_price_range(close: float, min_close: float, max_close: float) -> bool:
    return min_close <= close <= max_close


def passes_cap_filter(
    *,
    filters: RebalanceFilters,
    as_of_date: str,
    indicators: List[Dict[str, Any]],
    tag_rows: List[Dict[str, Any]],
) -> bool:
    _ = as_of_date, indicators, tag_rows
    if filters.cap_filter in ("", "none"):
        return True
    # devtools 演示：cap_filter 未接 tag/indicator 数据源时默认放行
    return True
