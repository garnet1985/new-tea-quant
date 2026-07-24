"""Calendar as-of hook 类型（slice_based on_calendar_asof 契约）。

消费者: enumerator
其它: contracts, hooks
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class CalendarAsOfContext:
    """on_calendar_asof 入参轻量类型（slice_based）。

    边界: 仅携带 as_of_date；完整 DataContext 由 hooks 侧组装。
    """

    as_of_date: str = ""


@dataclass
class CalendarAsOfResult:
    """on_calendar_asof 返回：当日选出的 stocks + session_state。

    边界: 策略钩子契约；不负责持仓推进。
    """

    as_of_date: str = ""
    stocks: List[str] = field(default_factory=list)
    session_state: Dict[str, Any] = field(default_factory=dict)
    stock_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)


__all__ = ["CalendarAsOfContext", "CalendarAsOfResult"]
