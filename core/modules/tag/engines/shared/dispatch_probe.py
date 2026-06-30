"""Tag timeline 探针：BacktestEngine 子进程入口（与生产 batch job 同路径）。"""
from __future__ import annotations

from typing import Any, Dict

from core.modules.backtest_engine.core.shared.types import JobContext
from core.modules.tag.services.execution.tag_job_pipeline import execute_tag_timeline_job

__all__ = ["execute_tag_probe_payload"]


def execute_tag_probe_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """BacktestEngine Probe 回调：走与 timeline.run 相同的 execute_tag_timeline_job。"""
    ctx = JobContext(
        job_id=str(payload.get("_job_id") or "tag_probe"),
        payload=dict(payload),
        run_name=str(payload.get("_run_name") or "tag:probe"),
    )
    return execute_tag_timeline_job(ctx)
