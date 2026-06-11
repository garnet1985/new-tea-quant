"""工作台加权进度计算。"""
from __future__ import annotations

from core.modules.strategy.execution_manager.workbench_run_envelope import (
    get_run_progress,
    run_envelope_apply_step_stage,
    run_envelope_mark_started,
    seed_workbench_run_envelope,
)
from core.modules.strategy.execution_manager.workbench_step_progress import (
    compute_run_progress,
    compute_step_progress_pct,
)
from core.modules.strategy.services.progress import ProgressRecorder


def test_compute_step_progress_pct_execute_midpoint():
    mid = compute_step_progress_pct("price", "execute", 0.5)
    assert 40.0 < mid < 60.0


def test_compute_run_progress_two_step_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(
        ProgressRecorder,
        "build_path",
        staticmethod(lambda channel, file_key: tmp_path / channel / f"{file_key}.json"),
    )
    sn, jid = "demo_strategy", "job-two"
    seed_workbench_run_envelope(sn, jid, [("enum", False), ("price", False)])
    run_envelope_mark_started(sn, jid)
    run_envelope_apply_step_stage(sn, jid, "enum", "execute", 0.5, counters={"done": 5, "total": 10})

    packed = get_run_progress(strategy_name=sn, job_id=jid)
    assert packed is not None
    rp = packed["run_progress"]
    assert 20.0 < float(rp["pct"]) < 35.0
    assert rp["substep"] == "enum"
    assert rp["substep_stage"] == "execute"
    assert rp["counter_text"] == "5/10"

    enum_step = next(r for r in packed["steps"] if r["step_name"] == "enum")
    assert enum_step["stage"] == "execute"
    assert enum_step["counters"]["done"] == 5


def test_get_run_progress_merges_enum_sidecar_without_regressing_to_one(tmp_path, monkeypatch):
    monkeypatch.setattr(
        ProgressRecorder,
        "build_path",
        staticmethod(lambda channel, file_key: tmp_path / channel / f"{file_key}.json"),
    )
    sn, jid = "demo_strategy", "job-abc"
    seed_workbench_run_envelope(sn, jid, [("enum", False)])
    run_envelope_mark_started(sn, jid)

    run_envelope_apply_step_stage(
        sn,
        jid,
        "enum",
        "execute",
        0.42,
        counters={"done": 21, "total": 50},
    )

    packed = get_run_progress(strategy_name=sn, job_id=jid)
    assert packed is not None
    enum_step = next(r for r in packed["steps"] if r["step_name"] == "enum")
    assert enum_step["status"] == "running"
    assert float(enum_step["progress"]) >= 40.0
    assert packed["run_progress"]["pct"] >= 40.0
