"""自管 running 槽：filelock 互斥与 pid 纠正。"""

from __future__ import annotations

from core.infra.job_pipeline import JobPipeline
from core.infra.job_pipeline.contracts import JobRunningBusyError
from core.infra.job_pipeline.core import registry_store
from core.infra.job_pipeline.core.store_io import atomic_write_json


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
    atomic_write_json(runtime / "job_pipeline_running.json", dead)
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


def test_recover_dead_pid_advances_queue(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    monkeypatch.setattr(registry_store, "_runtime_dir", lambda: runtime)
    from core.infra.job_pipeline.core import queue_store

    monkeypatch.setattr(queue_store, "queue_path", lambda: runtime / "job_pipeline_queue.json")

    dead = {
        "kind": "data_renew",
        "job_id": "dead-2",
        "resource_key": "*",
        "label": "更新",
        "domains": ["data"],
        "pid": 1_000_000_008,
        "started_at": "2020-01-01T00:00:00+00:00",
    }
    atomic_write_json(runtime / "job_pipeline_running.json", dead)
    JobPipeline.enqueue(
        {
            "kind": "tag_run",
            "resource_key": "demo/y",
            "label": "Tag: demo/y",
            "payload": {"tag_key": "demo/y"},
        }
    )
    seen = {}

    def _handler(spec):
        seen["job"] = dict(spec)
        return {"is_triggered": True, "job_id": spec.get("job_id")}

    JobPipeline.register_handler("tag_run", _handler)
    out = JobPipeline.recover()
    assert out.get("recovered") is True
    assert seen.get("job", {}).get("resource_key") == "demo/y"


def test_old_started_at_alone_is_not_stale_within_12h(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    monkeypatch.setattr(registry_store, "_runtime_dir", lambda: runtime)

    lease = JobPipeline.running_lease(
        kind="tag_run",
        job_id="job-long",
        resource_key="demo/z",
    )
    lease.acquire()
    path = runtime / "job_pipeline_running.json"
    raw = registry_store._read_json(path)
    # 2 小时前开跑、尚无 Progress：不应被 30min/2h 误伤
    raw["started_at"] = "2020-01-01T00:00:00+00:00"
    # 用「现在」附近的 started_at 模拟健康长任务
    from datetime import datetime, timedelta, timezone

    raw["started_at"] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    atomic_write_json(path, raw)

    job = JobPipeline.get_running_job()
    assert job is not None
    assert job.get("status") == "running"
    assert not job.get("stale")
    lease.release()


def test_stale_when_progress_heartbeat_old(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    monkeypatch.setattr(registry_store, "_runtime_dir", lambda: runtime)

    lease = JobPipeline.running_lease(
        kind="tag_run",
        job_id="job-stale",
        resource_key="demo/z",
    )
    lease.acquire()

    from core.infra.job_pipeline.core import liveness

    job = JobPipeline.get_running_job()
    assert job is not None
    job["progress"] = {"updated_at": 1_600_000_000, "percent": 10}
    marked = liveness.annotate_stale(job)
    assert marked.get("status") == "stale"
    assert marked.get("stale_source") == "progress"

    out = JobPipeline.abandon("job-stale")
    assert out.get("abandoned") is True
    assert JobPipeline.get_running_job() is None
