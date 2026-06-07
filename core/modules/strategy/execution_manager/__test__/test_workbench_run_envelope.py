"""工作台 run 信封与枚举进度合并。"""
from __future__ import annotations

from core.modules.strategy.execution_manager.workbench_run_envelope import (
    get_run_progress,
    run_envelope_mark_started,
    run_envelope_on_flow_progress,
    seed_workbench_run_envelope,
)
from core.modules.strategy.services.progress import ProgressRecorder


def test_get_run_progress_merges_enum_sidecar_without_regressing_to_one(tmp_path, monkeypatch):
    monkeypatch.setattr(
        ProgressRecorder,
        "build_path",
        staticmethod(lambda channel, file_key: tmp_path / channel / f"{file_key}.json"),
    )
    sn, jid = "demo_strategy", "job-abc"
    seed_workbench_run_envelope(sn, jid, [("enum", False)])
    run_envelope_mark_started(sn, jid)

    side = ProgressRecorder.for_strategy_run_step(sn, jid, "enum")
    side.record(
        {
            "strategy_name": sn,
            "run_id": jid,
            "step_name": "enum",
            "phase": "running",
            "progress_pct": 42,
            "done_jobs": 21,
            "total_jobs": 50,
        }
    )
    run_envelope_on_flow_progress(sn, jid, "enum", 42.0)

    packed = get_run_progress(strategy_name=sn, job_id=jid)
    assert packed is not None
    enum_step = next(r for r in packed["steps"] if r["step_name"] == "enum")
    assert enum_step["status"] == "running"
    assert float(enum_step["progress"]) >= 42.0
