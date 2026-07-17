"""Engine-owned calendar timeline driver."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence

from core.modules.backtest_engine.core.shared.types import JobContext
from core.modules.backtest_engine.core.timeline.hooks import TimelineHooks

logger = logging.getLogger(__name__)


class TimelineDriver:
    """引擎侧日历推进器。

    边界:
    - 负责: 过滤 open_dates、按日调用 TimelineHooks
    - 不负责: PIT / Investment / 策略语义
    - 调用方: TimelineWorkerExecute
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
    def resolve_open_dates(job_context: JobContext, hooks: TimelineHooks) -> List[str]:
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
    def resolve_period(job_context: JobContext, hooks: TimelineHooks) -> tuple:
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
        hooks: TimelineHooks,
        start_date: str = "",
        end_date: str = "",
    ) -> Dict[str, Any]:
        filtered = cls.filter_open_dates(
            open_dates, start_date=start_date, end_date=end_date
        )
        if not filtered:
            logger.warning(
                "TimelineDriver: 无有效 open_dates（start=%s end=%s）",
                start_date,
                end_date,
            )
            hooks.on_run_begin(())
            result = hooks.on_run_end(())
            return result if isinstance(result, dict) else {"success": True}

        hooks.on_run_begin(filtered)
        last_i = len(filtered) - 1
        for index, day in enumerate(filtered):
            hooks.on_day(day, index, is_last=(index == last_i))
        result = hooks.on_run_end(filtered)
        return result if isinstance(result, dict) else {"success": True}

    @classmethod
    def run_for_job(
        cls,
        job_context: JobContext,
        hooks: TimelineHooks,
    ) -> Dict[str, Any]:
        open_dates = cls.resolve_open_dates(job_context, hooks)
        start_date, end_date = cls.resolve_period(job_context, hooks)
        return cls.run(
            open_dates=open_dates,
            hooks=hooks,
            start_date=start_date,
            end_date=end_date,
        )


__all__ = ["TimelineDriver"]
