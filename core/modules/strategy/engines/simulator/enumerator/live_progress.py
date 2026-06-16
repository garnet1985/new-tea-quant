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


__all__ = [
    "format_elapsed_seconds",
    "print_enumeration_progress_line",
    "publish_enumeration_execute_progress",
]
