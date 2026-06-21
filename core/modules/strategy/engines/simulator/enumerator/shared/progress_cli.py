#!/usr/bin/env python3
"""枚举 execute 阶段实时进度：侧车 JSON、编排信封、终端输出。"""

from __future__ import annotations

import sys
from typing import Any, Dict, Optional

from core.modules.strategy.services.progress import ProgressRecorder


def format_elapsed_seconds(seconds: Optional[float]) -> str:
    if seconds is None:
        return ""
    try:
        s = max(0.0, float(seconds))
    except (TypeError, ValueError):
        return ""
    if s < 60.0:
        return f"{s:.1f}s"
    minutes = int(s // 60)
    rem = s - minutes * 60
    if rem < 1.0:
        return f"{minutes}m"
    return f"{minutes}m{rem:.0f}s"


def publish_enumeration_execute_progress(
    *,
    strategy_name: str,
    run_id: str,
    done: int,
    total: int,
    sidecar_extra: Optional[Dict[str, Any]] = None,
    update_envelope: bool = True,
) -> int:
    """写入 enum 步骤侧车；可选同步工作台 run envelope。返回 execute 局部 0～100。"""
    sn = str(strategy_name or "").strip()
    rid = str(run_id or "").strip()
    total_n = max(1, int(total))
    done_n = max(0, min(int(done), total_n))
    pct = min(100, int(done_n * 100 / total_n))

    if not sn or not rid:
        return pct

    payload: Dict[str, Any] = {
        "strategy_name": sn,
        "run_id": rid,
        "step_name": "enum",
        "phase": "running",
        "status": "running",
        "progress_pct": pct,
        "done_jobs": done_n,
        "total_jobs": total_n,
    }
    if sidecar_extra:
        payload.update(sidecar_extra)

    ProgressRecorder.for_strategy_run_step(sn, rid, "enum").record(payload)

    if update_envelope:
        from core.modules.strategy.execution_manager.workbench_run_envelope import (
            run_envelope_apply_step_stage,
        )

        run_envelope_apply_step_stage(
            sn,
            rid,
            "enum",
            "execute",
            pct / 100.0,
            counters={"done": done_n, "total": total_n},
        )
    return pct


def print_enumeration_progress_line(
    *,
    progress_pct: int,
    done: int,
    total: int,
    last_printed_pct: int,
    min_delta: int = 5,
    elapsed_seconds: Optional[float] = None,
) -> int:
    """终端一行进度（与 scan 风格一致）。返回更新后的 last_printed_pct。"""
    pct = int(progress_pct)
    if pct >= 100 and last_printed_pct >= 100:
        return last_printed_pct
    if pct < 100 and last_printed_pct >= 0 and pct - last_printed_pct < min_delta:
        return last_printed_pct
    elapsed_text = format_elapsed_seconds(elapsed_seconds)
    if elapsed_text:
        print(
            f"  进度：{pct}%（{done}/{total}）已用 {elapsed_text}",
            file=sys.stdout,
            flush=True,
        )
    else:
        print(f"  进度：{pct}%（{done}/{total}）", file=sys.stdout, flush=True)
    return pct


def format_calendar_slice_plan_line(plan: Dict[str, Any]) -> str:
    """Runtime Planner 摘要（CLI 一行）。"""
    if not isinstance(plan, dict):
        return ""
    budget = plan.get("memory_budget_mb")
    budget_s = f"{float(budget):.0f}MB" if budget is not None else "?"
    mb_slice = plan.get("mb_per_slice")
    mb_s = f"{float(mb_slice):.0f}MB" if mb_slice is not None else "?"
    return (
        f"  calendar_slice · 片宽={plan.get('slice_open_days')}开市日 "
        f"reader={plan.get('reader_workers')} "
        f"preload={plan.get('current_preload_depth')}/{plan.get('ideal_preload_ceiling')} "
        f"queue={plan.get('queue_capacity')} "
        f"budget={budget_s} (payload≈{mb_s}/片)"
    )


def print_calendar_slice_plan_line(plan: Dict[str, Any]) -> None:
    line = format_calendar_slice_plan_line(plan)
    if line:
        print(line, file=sys.stdout, flush=True)


def publish_calendar_slice_runtime_plan(
    *,
    strategy_name: str,
    run_id: str,
    plan: Dict[str, Any],
    done: Optional[int] = None,
    total: Optional[int] = None,
) -> None:
    """写入 enum 侧车，供主进程 poll 打印 plan（子进程 logger 不可见于 CLI）。"""
    sn = str(strategy_name or "").strip()
    rid = str(run_id or "").strip()
    if not sn or not rid or not isinstance(plan, dict):
        return
    rec = ProgressRecorder.for_strategy_run_step(sn, rid, "enum")
    prev = rec.get_progress() or {}
    try:
        done_n = int(done if done is not None else prev.get("done_jobs") or 0)
    except (TypeError, ValueError):
        done_n = 0
    try:
        total_n = int(total if total is not None else prev.get("total_jobs") or 0)
    except (TypeError, ValueError):
        total_n = 0
    publish_enumeration_execute_progress(
        strategy_name=sn,
        run_id=rid,
        done=done_n,
        total=max(1, total_n),
        sidecar_extra={"calendar_slice_runtime_plan": dict(plan)},
    )


__all__ = [
    "format_calendar_slice_plan_line",
    "format_elapsed_seconds",
    "print_calendar_slice_plan_line",
    "print_enumeration_progress_line",
    "publish_calendar_slice_runtime_plan",
    "publish_enumeration_execute_progress",
]
