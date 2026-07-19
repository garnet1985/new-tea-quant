"""Engine-owned timeline driver（按 Timeline.points 推进）。"""
from __future__ import annotations

import logging
from typing import Any, Dict

from core.modules.backtest_engine.core.shared.types import JobContext
from core.modules.backtest_engine.core.timeline.hooks import TimelineHooks
from core.modules.backtest_engine.core.timeline.timeline import Timeline

logger = logging.getLogger(__name__)


class TimelineDriver:
    """引擎侧时间轴推进器。

    边界:
    - 负责: 解析 Timeline、裁剪、按 point 调用 TimelineHooks
    - 不负责: PIT / 策略语义 / trade-calendar 默认构造
    - 调用方: TimelineWorkerExecute
    """

    @classmethod
    def resolve_timeline(cls, job_context: JobContext, hooks: TimelineHooks) -> Timeline:
        """解析时间轴：必须由 hooks.resolve_timeline 注入（可在其内读 payload）。"""
        resolver = getattr(hooks, "resolve_timeline", None)
        if not callable(resolver):
            raise ValueError(
                "TimelineHooks 必须实现 resolve_timeline(job_context) -> Timeline"
            )
        timeline = resolver(job_context)
        if not isinstance(timeline, Timeline):
            raise TypeError(
                f"resolve_timeline 必须返回 Timeline，实际: {type(timeline).__name__}"
            )
        return timeline

    @classmethod
    def run(cls, *, timeline: Timeline, hooks: TimelineHooks) -> Dict[str, Any]:
        clipped = timeline.clipped()
        if not clipped.points:
            logger.warning(
                "TimelineDriver: 无有效 points（kind=%s start=%s end=%s）",
                timeline.kind,
                timeline.start,
                timeline.end,
            )
            empty = Timeline(
                points=(),
                start=timeline.start,
                end=timeline.end,
                kind=timeline.kind,
                meta=dict(timeline.meta),
            )
            hooks.on_run_begin(empty)
            result = hooks.on_run_end(empty)
            return result if isinstance(result, dict) else {"success": True}

        hooks.on_run_begin(clipped)
        last_i = len(clipped.points) - 1
        for index, point in enumerate(clipped.points):
            hooks.on_tick(point, index, is_last=(index == last_i))
        result = hooks.on_run_end(clipped)
        return result if isinstance(result, dict) else {"success": True}

    @classmethod
    def run_for_job(
        cls,
        job_context: JobContext,
        hooks: TimelineHooks,
    ) -> Dict[str, Any]:
        timeline = cls.resolve_timeline(job_context, hooks)
        return cls.run(timeline=timeline, hooks=hooks)


__all__ = ["TimelineDriver"]
