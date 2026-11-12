"""JobPipeline 公开 API 契约测试（对齐 API.md）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.infra.job_pipeline import JobPipeline
from core.infra.job_pipeline.contracts import JobRunningBusyError
from core.infra.job_pipeline.core import queue_store, registry_store


@pytest.fixture
def pipeline_runtime(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    monkeypatch.setattr(registry_store, "_runtime_dir", lambda: runtime)
    monkeypatch.setattr(queue_store, "queue_path", lambda: runtime / "job_pipeline_queue.json")
    # 清空进程内 handler，避免跨用例污染
    from core.infra.job_pipeline import job_pipeline as jp_mod

    jp_mod._HANDLERS.clear()
    yield runtime
    jp_mod._HANDLERS.clear()


def test_facade_importable() -> None:
    assert JobPipeline is not None
    for name in (
        "get_running_job",
        "has_running_job",
        "list_jobs",
        "get_job",
        "running_lease",
        "enqueue",
        "submit",
        "cancel",
        "is_cancel_requested",
        "advance",
        "notify_job_finished",
        "recover",
        "abandon",
        "register_handler",
    ):
        assert callable(getattr(JobPipeline, name))


def test_register_handler_rejects_empty_kind(pipeline_runtime) -> None:
    with pytest.raises(ValueError):
        JobPipeline.register_handler("", lambda spec: {})


def test_running_lease_and_read_apis(pipeline_runtime) -> None:
    assert JobPipeline.has_running_job() is False
    assert JobPipeline.get_running_job() is None
    assert JobPipeline.list_jobs() == []

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
    assert JobPipeline.get_job("job-a")["job_id"] == "job-a"
    assert len(JobPipeline.list_jobs()) == 1

    busy = JobPipeline.running_lease(kind="strategy_run", job_id="job-b", resource_key="s1")
    with pytest.raises(JobRunningBusyError):
        busy.acquire()

    lease.release()
    assert JobPipeline.has_running_job() is False


def test_enqueue_submit_cancel_pending(pipeline_runtime) -> None:
    out = JobPipeline.enqueue(
        {
            "kind": "tag_run",
            "resource_key": "demo/y",
            "label": "Tag: demo/y",
            "payload": {"tag_key": "demo/y"},
        }
    )
    assert out.get("queued") is True
    jid = out["job_id"]
    jobs = JobPipeline.list_jobs()
    assert any(row.get("job_id") == jid and row.get("status") == "pending" for row in jobs)
    assert JobPipeline.get_job(jid)["status"] == "pending"

    cancelled = JobPipeline.cancel(jid)
    assert cancelled.get("cancelled") is True
    assert JobPipeline.get_job(jid) is None


def test_submit_idle_calls_handler(pipeline_runtime) -> None:
    seen = {}

    def _handler(spec):
        seen["spec"] = dict(spec)
        return {"is_triggered": True, "job_id": "from-handler"}

    JobPipeline.register_handler("tag_run", _handler)
    out = JobPipeline.submit(
        {
            "kind": "tag_run",
            "resource_key": "demo/z",
            "payload": {"tag_key": "demo/z"},
        }
    )
    assert out.get("is_triggered") is True
    assert seen["spec"]["resource_key"] == "demo/z"


def test_submit_busy_enqueues(pipeline_runtime) -> None:
    lease = JobPipeline.running_lease(
        kind="data_renew",
        job_id="hold",
        resource_key="*",
    )
    lease.acquire()
    out = JobPipeline.submit(
        {
            "kind": "tag_run",
            "resource_key": "demo/q",
            "payload": {"tag_key": "demo/q"},
        }
    )
    assert out.get("queued") is True
    lease.release()


def test_cancel_running_sets_flag(pipeline_runtime) -> None:
    lease = JobPipeline.running_lease(
        kind="tag_run",
        job_id="job-cancel",
        resource_key="demo/c",
    )
    lease.acquire()
    out = JobPipeline.cancel("job-cancel")
    assert out.get("cancelled") is True
    assert out.get("cancel_requested") is True
    assert JobPipeline.is_cancel_requested("job-cancel") is True
    lease.release()


def test_recover_dead_pid_and_advance(pipeline_runtime) -> None:
    dead = {
        "kind": "data_renew",
        "job_id": "dead-1",
        "resource_key": "*",
        "label": "更新",
        "domains": ["data"],
        "pid": 1_000_000_009,
        "started_at": "2020-01-01T00:00:00+00:00",
    }
    registry_store._atomic_write(pipeline_runtime / "job_pipeline_running.json", dead)
    JobPipeline.enqueue(
        {
            "kind": "tag_run",
            "resource_key": "demo/adv",
            "payload": {"tag_key": "demo/adv"},
        }
    )
    seen = {}

    def _handler(spec):
        seen["job"] = dict(spec)
        return {"is_triggered": True, "job_id": spec.get("job_id")}

    JobPipeline.register_handler("tag_run", _handler)
    out = JobPipeline.recover()
    assert out.get("recovered") is True
    assert seen.get("job", {}).get("resource_key") == "demo/adv"


def test_notify_job_finished_advances(pipeline_runtime) -> None:
    JobPipeline.enqueue(
        {
            "kind": "tag_run",
            "resource_key": "demo/n",
            "payload": {"tag_key": "demo/n"},
        }
    )
    seen = {}

    def _handler(spec):
        seen["ok"] = True
        return {"is_triggered": True}

    JobPipeline.register_handler("tag_run", _handler)
    JobPipeline.notify_job_finished()
    assert seen.get("ok") is True


def test_abandon_releases_running(pipeline_runtime) -> None:
    lease = JobPipeline.running_lease(
        kind="tag_run",
        job_id="job-abandon",
        resource_key="demo/a",
    )
    lease.acquire()
    out = JobPipeline.abandon("job-abandon")
    assert out.get("abandoned") is True
    assert JobPipeline.get_running_job() is None


def test_get_running_job_not_stale_within_wall_clock(pipeline_runtime) -> None:
    lease = JobPipeline.running_lease(
        kind="tag_run",
        job_id="job-long",
        resource_key="demo/long",
    )
    lease.acquire()
    path = pipeline_runtime / "job_pipeline_running.json"
    raw = registry_store._read_json(path)
    raw["started_at"] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    registry_store._atomic_write(path, raw)
    job = JobPipeline.get_running_job()
    assert job is not None
    assert job.get("status") == "running"
    lease.release()
