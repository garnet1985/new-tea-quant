"""自管 running 槽：filelock 互斥与 pid 纠正。"""

from __future__ import annotations

from core.infra.job_pipeline import JobPipeline
from core.infra.job_pipeline.contracts import JobRunningBusyError
from core.infra.job_pipeline.core import registry_store


def test_acquire_release_roundtrip(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    monkeypatch.setattr(registry_store, "_runtime_dir", lambda: runtime)

    lease = JobPipeline.running_lease(
        kind="tag_run",
        job_id="job-a",
        resource_key="demo/x",
        label="Tag: demo/x",
        domains=["tag"],
    )
    snap = lease.acquire()
    assert snap["job_id"] == "job-a"
    assert JobPipeline.has_running_job() is True
    running = JobPipeline.get_running_job()
    assert running is not None
    assert running["kind"] == "tag_run"

    busy = JobPipeline.running_lease(
        kind="strategy_run",
        job_id="job-b",
        resource_key="s1",
    )
    try:
        busy.acquire()
        raise AssertionError("expected busy")
    except JobRunningBusyError as exc:
        assert exc.existing.get("job_id") == "job-a"

    lease.release()
    assert JobPipeline.has_running_job() is False
    assert not (runtime / "job_pipeline_running.json").is_file()


def test_stale_pid_is_cleared(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    monkeypatch.setattr(registry_store, "_runtime_dir", lambda: runtime)

    dead = {
        "kind": "data_renew",
        "job_id": "dead-1",
        "resource_key": "*",
        "label": "更新",
        "domains": ["data"],
        "pid": 1_000_000_007,
        "started_at": "2020-01-01T00:00:00+00:00",
    }
    registry_store._atomic_write(runtime / "job_pipeline_running.json", dead)
    assert JobPipeline.get_running_job() is None


def test_request_cancel_running(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    monkeypatch.setattr(registry_store, "_runtime_dir", lambda: runtime)

    lease = JobPipeline.running_lease(
        kind="tag_run",
        job_id="job-cancel",
        resource_key="demo/x",
    )
    lease.acquire()
    out = JobPipeline.cancel("job-cancel")
    assert out["cancelled"] is True
    assert out.get("cancel_requested") is True
    assert JobPipeline.is_cancel_requested("job-cancel") is True
    lease.release()
