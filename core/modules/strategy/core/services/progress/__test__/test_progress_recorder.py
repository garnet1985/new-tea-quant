"""Tests for ProgressRecorder (job JSON via Progress.channel)."""

from __future__ import annotations

from core.infra.progress import Progress
from core.modules.strategy.core.services.progress import ProgressRecorder


def test_record_and_get_progress(tmp_path, monkeypatch):
    monkeypatch.setenv("NTQ_PROGRESS_DIR", str(tmp_path / "jobs"))

    rec = ProgressRecorder.for_strategy_workbench_run("demo/x", "job1")
    rec.record({"phase": "running", "schema": "workbench_run_v1"})
    loaded = rec.get_progress()
    assert loaded is not None
    assert loaded["phase"] == "running"
    assert "updated_at" in loaded
    assert (
        Progress.channel.read("strategy-workbench-run", "demo/x__job1") is not None
    )

    rec.reset()
    assert rec.get_progress() is None
