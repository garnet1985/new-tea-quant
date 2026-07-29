"""Tag pipeline 主进程钩子上下文（保证 RunCallbacks 可 pickle）。

消费者: TagEntityPipeline, TagSlicePipeline

``TimelineWorkerExecute`` 会 pickle 整份 ``RunCallbacks``；嵌套函数 / lambda
会导致 process pool 任务立即失败。主进程状态放 ClassVar，回调用 classmethod。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, ClassVar, Dict, Optional

from core.modules.backtest_engine.contracts import JobReport, RunProgress
from core.modules.tag.core.engines.shared.services.tag_value_flush import (
    TagValueFlushService,
)


@dataclass
class TagPipelineRunContext:
    """单次 pipeline.run 的主进程可变状态。"""

    flush: TagValueFlushService
    total_jobs: int
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None
    finished: int = 0
    ok: int = 0
    fail: int = 0
    tag_values_count: int = 0


class TagPipelineHooks:
    """主进程 on_task_result 分派（可 pickle 的 classmethod）。"""

    _ctx: ClassVar[Optional[TagPipelineRunContext]] = None

    @classmethod
    def bind(cls, ctx: TagPipelineRunContext) -> None:
        cls._ctx = ctx

    @classmethod
    def clear(cls) -> None:
        cls._ctx = None

    @classmethod
    def on_task_result(cls, report: JobReport, progress: RunProgress) -> None:
        ctx = cls._ctx
        if ctx is None:
            return
        ctx.finished += 1
        if report.success:
            ctx.ok += 1
        else:
            ctx.fail += 1
        data = report.data if isinstance(report.data, dict) else {}
        rows = data.get("tag_values") or []
        if rows:
            ctx.tag_values_count += ctx.flush.extend(rows)
        if ctx.on_progress is not None:
            total = max(int(ctx.total_jobs), 1)
            ctx.on_progress(
                {
                    "finished": ctx.finished,
                    "total": total,
                    "ok": ctx.ok,
                    "fail": ctx.fail,
                    "progress_pct": min(100.0, ctx.finished / total * 100.0),
                }
            )


__all__ = ["TagPipelineHooks", "TagPipelineRunContext"]
