"""``workbench_step_progress`` 单元测试。"""
from __future__ import annotations

from core.modules.strategy.execution_manager.workbench_step_progress import (
    compute_run_progress,
    compute_step_progress_pct,
)


def test_step_progress_monotonic_across_stages():
    load_end = compute_step_progress_pct("enum", "load", 1.0)
    dispatch_end = compute_step_progress_pct("enum", "dispatch", 1.0)
    execute_mid = compute_step_progress_pct("enum", "execute", 0.5)
    assert load_end < dispatch_end < execute_mid


def test_run_progress_completed_steps():
    steps = [
        {"step_name": "enum", "status": "completed", "progress": 100.0},
        {"step_name": "price", "status": "running", "progress": 50.0, "stage": "execute"},
    ]
    rp = compute_run_progress(["enum", "price"], steps)
    assert rp["pct"] == 75.0
    assert rp["substep"] == "price"
