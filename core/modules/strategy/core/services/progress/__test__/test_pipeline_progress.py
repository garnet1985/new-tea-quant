"""Tests for PipelineProgress service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from core.modules.strategy.core.services.progress import (
    PipelineProgress,
    ProgressRecorder,
)


def _patch_recorder(tmp_path, monkeypatch):
    def _build(channel, file_key):
        return tmp_path / "progress" / channel / f"{file_key}.json"

    monkeypatch.setattr(ProgressRecorder, "build_path", staticmethod(_build))


def test_seed_enter_tick_complete(tmp_path, monkeypatch):
    _patch_recorder(tmp_path, monkeypatch)
    PipelineProgress.seed("demo/x", "job1", pipeline_name="enum")

    with PipelineProgress.bind("demo/x", "job1") as prog:
        prog.mark_running()
        prog.enter_step("load")
        prog.complete_step("load")
        prog.enter_step("dispatch")
        prog.complete_step("dispatch")
        prog.enter_step("execute")
        prog.tick_execute(5, 10)
        assert prog.to_dict()["step"]["counters"] == {"done": 5, "total": 10}
        mid = float(prog.to_dict()["progress"])
        assert 0 < mid < 100
        prog.tick_execute(10, 10)
        prog.complete_step("execute")
        prog.enter_step("report")
        prog.complete_step("report")
        prog.complete(result={"version_id": "v3"})

    doc = PipelineProgress.get("demo/x", "job1")
    assert doc is not None
    assert doc["status"] == "completed"
    assert doc["progress"] == 100.0
    assert doc["result"]["version_id"] == "v3"
    names = [x["name"] for x in doc["completed_steps"]]
    assert names == ["load", "dispatch", "execute", "report"]


def test_fail_keeps_completed_steps(tmp_path, monkeypatch):
    _patch_recorder(tmp_path, monkeypatch)
    PipelineProgress.seed("demo/x", "job2", pipeline_name="price")
    with PipelineProgress.bind("demo/x", "job2") as prog:
        prog.mark_running()
        prog.enter_step("load")
        prog.complete_step()
        prog.enter_step("execute")
        prog.tick_execute(1, 4)
        prog.fail("boom")

    doc = PipelineProgress.get("demo/x", "job2")
    assert doc["status"] == "failed"
    assert doc["error"] == "boom"
    assert doc["completed_steps"][0]["name"] == "load"
    assert doc["step"]["name"] == "execute"


def test_stale_running_marked_failed(tmp_path, monkeypatch):
    import json

    _patch_recorder(tmp_path, monkeypatch)
    PipelineProgress.seed("demo/x", "job3", pipeline_name="enum")
    with PipelineProgress.bind("demo/x", "job3") as prog:
        prog.mark_running()
        prog.enter_step("execute")
        path = ProgressRecorder.for_strategy_workbench_run(
            "demo/x", "job3"
        ).recorder_path
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["updated_at"] = (
            datetime.now(timezone.utc) - timedelta(hours=2)
        ).isoformat()
        path.write_text(json.dumps(raw), encoding="utf-8")

    doc = PipelineProgress.get("demo/x", "job3", apply_stale=True)
    assert doc["status"] == "failed"
    assert "超时" in doc["error"]


def test_bound_facades_noop_without_bind(tmp_path, monkeypatch):
    _patch_recorder(tmp_path, monkeypatch)
    PipelineProgress.enter_step_bound("load")
    PipelineProgress.tick_execute_bound(1, 2)
    assert PipelineProgress.current() is None
