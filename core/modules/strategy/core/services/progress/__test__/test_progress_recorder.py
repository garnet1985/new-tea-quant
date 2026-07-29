"""Tests for ProgressRecorder disk IO."""

from __future__ import annotations

from core.modules.strategy.core.services.progress import ProgressRecorder


def test_record_and_get_progress(tmp_path, monkeypatch):
    def _build(channel, file_key):
        return tmp_path / "progress" / channel / f"{file_key}.json"

    monkeypatch.setattr(ProgressRecorder, "build_path", staticmethod(_build))

    rec = ProgressRecorder.for_strategy_workbench_run("demo/x", "job1")
    rec.record({"phase": "running", "schema": "workbench_run_v1"})
    loaded = rec.get_progress()
    assert loaded is not None
    assert loaded["phase"] == "running"
    assert "updated_at" in loaded

    rec.reset()
    assert rec.get_progress() is None
