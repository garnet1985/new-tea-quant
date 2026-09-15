"""决策者时间线：枚举事件按日索引 + as-of 胜率。

本文件:
- DecisionTimeline: buy/sell 按日、机会展示投影、截止 D 的策略胜率
  边界: 引擎可用完整 EnumResult 排程；展示字段不含本笔未来
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from core.modules.strategy.core.engines.portfolio.data_class import PortfolioEvent
from core.modules.strategy.core.engines.shared.enum_result_contract.enum_result import (
    EnumResult,
)
from core.tables.stock.stock_st_periods.st_period_rules import bare_stock_name

logger = logging.getLogger(__name__)


def lot_key(entity_id: str, investment_id: str) -> str:
    return f"{str(entity_id or '').strip()}\t{str(investment_id or '').strip()}"


_STATUS_LABELS = {"st": "ST", "star_st": "*ST"}


def normalize_status_tags(raw: Any) -> Tuple[str, ...]:
    out: List[str] = []
    if not isinstance(raw, (list, tuple)):
        return ()
    for item in raw:
        tag = str(item or "").strip().lower()
        if tag and tag not in out:
            out.append(tag)
    return tuple(out)


def format_status_tags(tags: Sequence[str]) -> str:
    labels: List[str] = []
    for tag in tags or ():
        label = _STATUS_LABELS.get(str(tag).strip().lower())
        if label and label not in labels:
            labels.append(label)
    return " ".join(labels)


def _enum_status_tags(row: Optional[EnumResult]) -> Tuple[str, ...]:
    if row is None:
        return ()
    return normalize_status_tags(getattr(row, "stock_status_at_trigger", ()) or ())


def _enum_display_name(
    row: Optional[EnumResult],
    entity_id: str,
    *,
    name_lookup: Optional[Callable[[str], str]] = None,
) -> str:
    stored = str(getattr(row, "stock_name", "") or "").strip() if row is not None else ""
    if stored:
        return stored
    raw = ""
    if callable(name_lookup):
        try:
            raw = str(name_lookup(entity_id) or "").strip()
        except Exception as exc:
            logger.debug("证券名称查找失败 %s: %s", entity_id, exc)
            raw = ""
    return bare_stock_name(raw)


@dataclass(frozen=True)
class AsOfStats:
    """截止 D 之前已结束机会的胜率 / 平均 ROI。"""

    sample_size: int
    wins: int
    win_rate: Optional[float]
    avg_roi: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_size": int(self.sample_size),
            "wins": int(self.wins),
            "win_rate": self.win_rate,
            "avg_roi": self.avg_roi,
        }


@dataclass
class DayOpportunity:
    """当日一条可买机会（编号由引擎按当天列表赋）。"""

    local_id: int
    entity_id: str
    investment_id: str
    entry_price_raw: float
    entry_price_hfq: float
    bar_volume: Optional[float]
    name: str = ""
    status_tags: Tuple[str, ...] = ()
    stats: Optional[AsOfStats] = None
    ticker_stats: Optional[AsOfStats] = None

    @property
    def key(self) -> str:
        return lot_key(self.entity_id, self.investment_id)


@dataclass
class DecisionTimeline:
    """一份 enum 展开后的买卖日历。"""

    events: List[PortfolioEvent] = field(default_factory=list)
    rows: Dict[str, EnumResult] = field(default_factory=dict)
    start_date: str = ""
    end_date: str = ""
    buys_by_date: Dict[str, List[PortfolioEvent]] = field(default_factory=dict)
    sells_by_date: Dict[str, List[PortfolioEvent]] = field(default_factory=dict)
    dates: List[str] = field(default_factory=list)

    @classmethod
    def from_events(
        cls,
        events: Sequence[PortfolioEvent],
        *,
        rows: Optional[Iterable[EnumResult]] = None,
        start_date: str = "",
        end_date: str = "",
    ) -> "DecisionTimeline":
        row_map: Dict[str, EnumResult] = {}
        for row in rows or ():
            eid = str(getattr(row, "entity_id", "") or "").strip()
            iid = str(getattr(row, "investment_id", "") or "").strip()
            if eid and iid:
                row_map[lot_key(eid, iid)] = row
        buys: Dict[str, List[PortfolioEvent]] = {}
        sells: Dict[str, List[PortfolioEvent]] = {}
        ordered = list(events)
        ordered.sort(
            key=lambda e: (
                str(e.date or ""),
                0 if e.is_buy() else 1,
                str(e.entity_id or ""),
                str(e.investment_id or ""),
            )
        )
        dates: List[str] = []
        seen = set()
        for event in ordered:
            date = str(event.date or "").strip()
            if not date:
                continue
            if date not in seen:
                seen.add(date)
                dates.append(date)
            if event.is_buy():
                buys.setdefault(date, []).append(event)
            elif event.is_sell():
                sells.setdefault(date, []).append(event)
        dates.sort()
        return cls(
            events=ordered,
            rows=row_map,
            start_date=str(start_date or "").strip(),
            end_date=str(end_date or "").strip(),
            buys_by_date=buys,
            sells_by_date=sells,
            dates=dates,
        )

    def buys_on(self, date: str) -> List[PortfolioEvent]:
        return list(self.buys_by_date.get(str(date or "").strip()) or ())

    def sells_on(self, date: str) -> List[PortfolioEvent]:
        return list(self.sells_by_date.get(str(date or "").strip()) or ())

    def first_buy_date(self) -> str:
        for date in self.dates:
            if self.buys_on(date):
                return date
        return ""

    def dates_after(self, date: str) -> List[str]:
        cur = str(date or "").strip()
        if not cur:
            return list(self.dates)
        return [item for item in self.dates if item > cur]

    def asof_stats(self, as_of: str, *, entity_id: str = "") -> AsOfStats:
        """``exit_date < D`` 的已结束机会；可再限该标的。"""
        cutoff = str(as_of or "").strip()
        eid = str(entity_id or "").strip()
        rois: List[float] = []
        wins = 0
        for row in self.rows.values():
            exit_date = str(getattr(row, "exit_date", "") or "").strip()
            if not exit_date or not cutoff or not (exit_date < cutoff):
                continue
            if eid and str(getattr(row, "entity_id", "") or "").strip() != eid:
                continue
            roi = float(getattr(row, "weighted_roi", 0.0) or 0.0)
            rois.append(roi)
            if roi > 0:
                wins += 1
        n = len(rois)
        if n <= 0:
            return AsOfStats(sample_size=0, wins=0, win_rate=None, avg_roi=None)
        return AsOfStats(
            sample_size=n,
            wins=wins,
            win_rate=float(wins) / float(n),
            avg_roi=sum(rois) / float(n),
        )

    def exit_label(self, entity_id: str, investment_id: str) -> Tuple[str, str]:
        """只读日志用：目标名 / 原因。不含未来价。"""
        row = self.rows.get(lot_key(entity_id, investment_id))
        if row is None:
            return "", ""
        reason = str(getattr(row, "exit_reason", "") or "").strip()
        goals = list(getattr(row, "completed_goals", ()) or ())
        names: List[str] = []
        for goal in goals:
            name = str(getattr(goal, "name", "") or "").strip()
            if name:
                names.append(name)
        return " / ".join(names), reason

    def row_for(self, entity_id: str, investment_id: str) -> Optional[EnumResult]:
        return self.rows.get(lot_key(entity_id, investment_id))

    def display_name(
        self,
        entity_id: str,
        investment_id: str = "",
        *,
        name_lookup: Optional[Callable[[str], str]] = None,
    ) -> str:
        row = self.row_for(entity_id, investment_id) if investment_id else None
        return _enum_display_name(row, entity_id, name_lookup=name_lookup)

    def status_tags(self, entity_id: str, investment_id: str) -> Tuple[str, ...]:
        return _enum_status_tags(self.row_for(entity_id, investment_id))

    def opportunities_on(
        self,
        date: str,
        *,
        name_lookup: Optional[Callable[[str], str]] = None,
    ) -> List[DayOpportunity]:
        stats = self.asof_stats(date)
        out: List[DayOpportunity] = []
        for idx, event in enumerate(self.buys_on(date), start=1):
            eid = str(event.entity_id or "").strip()
            iid = str(event.investment_id or "").strip()
            row = self.row_for(eid, iid)
            ticker = self.asof_stats(date, entity_id=eid)
            out.append(
                DayOpportunity(
                    local_id=idx,
                    entity_id=eid,
                    investment_id=iid,
                    entry_price_raw=float(event.price or event.entry_price_raw or 0.0),
                    entry_price_hfq=float(getattr(event, "entry_price_hfq", 0.0) or 0.0),
                    bar_volume=event.bar_volume,
                    name=_enum_display_name(row, eid, name_lookup=name_lookup),
                    status_tags=_enum_status_tags(row),
                    stats=stats,
                    ticker_stats=ticker,
                )
            )
        return out


__all__ = [
    "AsOfStats",
    "DayOpportunity",
    "DecisionTimeline",
    "format_status_tags",
    "lot_key",
    "normalize_status_tags",
]
