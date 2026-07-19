"""Timeline progression hooks（中性 tick；非日历专属）。"""
from __future__ import annotations

from typing import Any, Dict, Protocol, runtime_checkable

from core.modules.backtest_engine.core.shared.types import JobContext
from core.modules.backtest_engine.core.timeline.timeline import Timeline


@runtime_checkable
class TimelineHooks(Protocol):
    """回测推进钩子。

    边界:
    - 负责: 注入/解析 Timeline、单点业务、run 汇总
    - 不负责: points 迭代（TimelineDriver）
    - 调用方: TimelineDriver；实现方: enumerator / tag / price_factor 等
    """

    def resolve_timeline(self, job_context: JobContext) -> Timeline:
        """注入时间轴（显式 API）。未自定义时由实现提供默认 calendar 轴。"""
        ...

    def on_run_begin(self, timeline: Timeline) -> None:
        ...

    def on_tick(self, point: str, index: int, *, is_last: bool) -> None:
        ...

    def on_run_end(self, timeline: Timeline) -> Dict[str, Any]:
        ...


__all__ = ["TimelineHooks"]
