"""Tests for ScanProgress disk helpers."""

from __future__ import annotations

from core.modules.strategy.core.services.progress import ProgressRecorder, ScanProgress


def _patch_recorder(tmp_path, monkeypatch):
    def _build(channel, file_key):
        return tmp_path / "progress" / channel / f"{file_key}.json"

    monkeypatch.setattr(ProgressRecorder, "build_path", staticmethod(_build))


def test_seed_tick_complete_poll(tmp_path, monkeypatch):
    _patch_recorder(tmp_path, monkeypatch)
    prog = ScanProgress.for_job("demo/x", "job1")
    prog.seed(demo=True, force=False)
    prog.mark_running()
    prog.tick(
        {
            "progress_pct": 40,
            "total_jobs": 10,
            "completed_jobs": 4,
            "failed_jobs": 0,
            "cancelled_jobs": 0,
            "last_job_id": "b1",
            "last_job_status": "ok",
        }
    )
    mid = ScanProgress.get_poll_dto("demo/x", "job1")
    assert mid is not None
    assert mid["status"] == "running"
    assert mid["progress"] == 40.0
    assert mid["done_jobs"] == 4

    prog.complete({"date": "2020-01-02", "total_opportunities": 0}, cache_key="")
    done = ScanProgress.get_poll_dto("demo/x", "job1")
    assert done["status"] == "completed"
    assert done["is_success"] is True
    assert done["report"]["date"] == "2020-01-02"


def test_fail_poll(tmp_path, monkeypatch):
    _patch_recorder(tmp_path, monkeypatch)
    prog = ScanProgress.for_job("demo/x", "job2")
    prog.seed(demo=False, force=True)
    prog.fail("nope")
    out = ScanProgress.get_poll_dto("demo/x", "job2")
    assert out["status"] == "failed"
    assert out["reason"] == "nope"
