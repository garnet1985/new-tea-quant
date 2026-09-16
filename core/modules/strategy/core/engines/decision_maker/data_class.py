"""决策者会话侧数据类与加载回调类型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.decision_maker.timeline import DayOpportunity

LoadBars = Callable[[str, str, int], List[Dict[str, Any]]]
LoadClose = Callable[[str, str], Optional[float]]
NameLookup = Callable[[str], str]
ReportLoader = Callable[..., Any]


@dataclass
class ExitNotice:
    """纪律出场后给 REPL 的一行日志。"""

    date: str
    entity_id: str
    name: str
    shares: int
    profit: float
    goal_names: str
    reason: str
    status_tags: Tuple[str, ...] = ()


@dataclass
class AdvanceResult:
    """``next`` 推进结果：是否走完、本站事件日志、当日机会。"""

    completed: bool
    current_date: str
    logs: List[ExitNotice] = field(default_factory=list)
    opportunities: List["DayOpportunity"] = field(default_factory=list)


@dataclass
class HoldingRow:
    """``holdings`` 一行；目标文案不含本笔未来价/日。"""

    entity_id: str
    name: str
    shares: int
    buy_date: str
    buy_price: float
    hold_days: int
    close: Optional[float]
    unrealized: Optional[float]
    goals: List[str]
    status_tags: Tuple[str, ...] = ()
    hold_unit: str = "natural_day"


__all__ = [
    "AdvanceResult",
    "ExitNotice",
    "HoldingRow",
    "LoadBars",
    "LoadClose",
    "NameLookup",
    "ReportLoader",
]
