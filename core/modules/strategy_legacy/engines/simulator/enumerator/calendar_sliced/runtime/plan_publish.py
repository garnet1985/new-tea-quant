#!/usr/bin/env python3
"""将 Runtime Plan 写入 enum 侧车（子进程 → 主进程 CLI）。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.runtime_plan import (
    CalendarSliceRuntimePlan,
)
from core.modules.strategy.engines.simulator.enumerator.shared.progress_cli import (
    publish_calendar_slice_runtime_plan,
)


def publish_runtime_plan_from_job(
    job_payload: Dict[str, Any],
    plan: CalendarSliceRuntimePlan,
    *,
    done: Optional[int] = None,
    total: Optional[int] = None,
) -> None:
    sn = str(job_payload.get("workbench_strategy_name") or "").strip()
    rid = str(job_payload.get("workbench_run_id") or "").strip()
    if not sn or not rid:
        return
    if total is None:
        try:
            total = int(job_payload.get("calendar_progress_total") or 0)
        except (TypeError, ValueError):
            total = 0
    publish_calendar_slice_runtime_plan(
        strategy_name=sn,
        run_id=rid,
        plan=plan.to_dict(),
        done=done,
        total=total,
    )


__all__ = ["publish_runtime_plan_from_job"]
