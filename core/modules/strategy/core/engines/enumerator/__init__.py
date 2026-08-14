"""枚举器包：把策略钩子经 BE RunCallbacks 挂入回测，并做 jobs/报告周边。

硬约束（详见 ``docs/notes/BOUNDARY_NOTES.md``「与 BacktestEngine 的关系」）:
- mode 下只有 **JobBuilder + JobExecutor**；勿再加 TimelineBuilder / JobSession
- 推进轴：BE 默认开市日（``run(start,end)``）；枚举器不复写 Timeline.points
- 可变状态：只挂 ``job_context.init``（BE hold）；TaskState 不是第二套 session
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pipeline import EnumeratorPipeline

__all__ = ["EnumeratorPipeline"]


def __getattr__(name: str):
    if name == "EnumeratorPipeline":
        from .pipeline import EnumeratorPipeline

        return EnumeratorPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
