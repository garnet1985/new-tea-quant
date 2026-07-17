"""Calendar day advancement: engine-owned loop, caller-owned per-day logic."""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence, runtime_checkable

from core.modules.backtest_engine.core.shared.types import JobContext

logger = logging.getLogger(__name__)

ExecuteFnLike = Callable[[JobContext], Any]


@runtime_checkable
class AdvancementHooks(Protocol):
    """日历推进钩子（entity / slice 共用面；日序差异在实现内）。

    边界:
    - 负责: 单日业务（tick / asof / scan）、run 汇总 dict
    - 不负责: open_dates 迭代本身（CalendarAdvancer）
    - 调用方: CalendarAdvancer；实现方: enumerator / 其他策略引擎
    """

    def on_run_begin(self, open_dates: Sequence[str]) -> None:
        ...

    def on_day(self, day: str, index: int, *, is_last: bool) -> None:
        ...

    def on_run_end(self, open_dates: Sequence[str]) -> Dict[str, Any]:
        """返回写入 JobReport.data 的 dict（应含 success 等）。"""
        ...


AdvancementHooksFactory = Callable[[JobContext], AdvancementHooks]


class CalendarAdvancer:
    """引擎侧日历推进器。

    边界:
    - 负责: 过滤 open_dates、按日调用 AdvancementHooks
    - 不负责: PIT / Investment / 策略 hooks
    - 调用方: entity / slice worker（advancement_hooks_factory 路径）
    """

    @staticmethod
    def filter_open_dates(
        open_dates: Sequence[str],
        *,
        start_date: str = "",
        end_date: str = "",
    ) -> List[str]:
        start = str(start_date or "").strip()
        end = str(end_date or "").strip()
        out: List[str] = []
        for day in open_dates:
            d = str(day or "").strip()
            if not d:
                continue
            if start and d < start:
                continue
            if end and d > end:
                continue
            out.append(d)
        return out

    @staticmethod
    def resolve_open_dates(job_context: JobContext, hooks: AdvancementHooks) -> List[str]:
        """优先 hooks.resolve_open_dates；否则 payload.open_dates / backtest_calendar。"""
        resolver = getattr(hooks, "resolve_open_dates", None)
        if callable(resolver):
            raw = resolver(job_context)
            if isinstance(raw, list):
                return [str(d).strip() for d in raw if str(d).strip()]

        payload = job_context.payload or {}
        raw = payload.get("open_dates")
        if isinstance(raw, list) and raw:
            return [str(d).strip() for d in raw if str(d).strip()]

        calendar = payload.get("backtest_calendar")
        if isinstance(calendar, dict):
            cal_dates = calendar.get("open_dates")
            if isinstance(cal_dates, list) and cal_dates:
                return [str(d).strip() for d in cal_dates if str(d).strip()]
        return []

    @staticmethod
    def resolve_period(job_context: JobContext, hooks: AdvancementHooks) -> tuple[str, str]:
        resolver = getattr(hooks, "resolve_period", None)
        if callable(resolver):
            period = resolver(job_context)
            if isinstance(period, (tuple, list)) and len(period) >= 2:
                return str(period[0] or "").strip(), str(period[1] or "").strip()

        payload = job_context.payload or {}
        start = str(payload.get("start_date") or "").strip()
        end = str(payload.get("end_date") or "").strip()
        if start and end:
            return start, end

        entity_shared = payload.get("entity_shared") or {}
        if isinstance(entity_shared, dict) and entity_shared:
            first = next(iter(entity_shared.values()), {}) or {}
            if isinstance(first, dict):
                return (
                    str(first.get("start") or "").strip(),
                    str(first.get("end") or "").strip(),
                )
        return "", ""

    @classmethod
    def run(
        cls,
        *,
        open_dates: Sequence[str],
        hooks: AdvancementHooks,
        start_date: str = "",
        end_date: str = "",
    ) -> Dict[str, Any]:
        filtered = cls.filter_open_dates(
            open_dates, start_date=start_date, end_date=end_date
        )
        if not filtered:
            logger.warning(
                "CalendarAdvancer: 无有效 open_dates（start=%s end=%s）",
                start_date,
                end_date,
            )
            hooks.on_run_begin(())
            result = hooks.on_run_end(())
            if isinstance(result, dict):
                return result
            return {"success": True}

        hooks.on_run_begin(filtered)
        last_i = len(filtered) - 1
        for index, day in enumerate(filtered):
            hooks.on_day(day, index, is_last=(index == last_i))
        result = hooks.on_run_end(filtered)
        if isinstance(result, dict):
            return result
        return {"success": True}

    @classmethod
    def run_for_job(
        cls,
        job_context: JobContext,
        hooks: AdvancementHooks,
    ) -> Dict[str, Any]:
        open_dates = cls.resolve_open_dates(job_context, hooks)
        start_date, end_date = cls.resolve_period(job_context, hooks)
        return cls.run(
            open_dates=open_dates,
            hooks=hooks,
            start_date=start_date,
            end_date=end_date,
        )


def run_with_advancement_factory(
    job_context: JobContext,
    factory: AdvancementHooksFactory,
) -> Dict[str, Any]:
    """Worker 入口：factory(job_context) → CalendarAdvancer.run_for_job。"""
    hooks = factory(job_context)
    return CalendarAdvancer.run_for_job(job_context, hooks)


class BoundAdvancementExecute:
    """可 pickle 的 ExecuteFn 适配器：包装 advancement_hooks_factory。

    供 ProcessPool / probe 复用既有 execute_fn 通道。
    """

    def __init__(self, factory: AdvancementHooksFactory) -> None:
        self.factory = factory

    def __call__(self, job_context: JobContext) -> Dict[str, Any]:
        return run_with_advancement_factory(job_context, self.factory)


def require_execute_xor_advancement(
    *,
    execute_fn: Optional[ExecuteFnLike] = None,
    advancement_hooks_factory: Optional[AdvancementHooksFactory] = None,
) -> None:
    has_exec = execute_fn is not None
    has_adv = advancement_hooks_factory is not None
    if has_exec == has_adv:
        raise ValueError(
            "BacktestEngine.run 需要恰好其一: execute_fn 或 advancement_hooks_factory"
        )


def resolve_worker_execute_fn(
    *,
    execute_fn: Optional[ExecuteFnLike] = None,
    advancement_hooks_factory: Optional[AdvancementHooksFactory] = None,
) -> ExecuteFnLike:
    require_execute_xor_advancement(
        execute_fn=execute_fn,
        advancement_hooks_factory=advancement_hooks_factory,
    )
    if advancement_hooks_factory is not None:
        return BoundAdvancementExecute(advancement_hooks_factory)
    assert execute_fn is not None
    return execute_fn


__all__ = [
    "AdvancementHooks",
    "AdvancementHooksFactory",
    "BoundAdvancementExecute",
    "CalendarAdvancer",
    "run_with_advancement_factory",
    "require_execute_xor_advancement",
    "resolve_worker_execute_fn",
]
