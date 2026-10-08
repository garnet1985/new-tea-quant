"""Tests for TaskLease mutual exclusion."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from core.infra.task_guard import TaskGuard
from core.infra.task_guard.contracts import TaskLeaseBusyError

pytestmark = pytest.mark.force_run


@pytest.fixture
def lease_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "task_guard_active.json"
    monkeypatch.setattr(
        "core.infra.task_guard.core.lease.task_lease.TaskLease.lease_path",
        staticmethod(lambda: path),
    )
    return path


def test_idle_then_busy_then_release(lease_file: Path):
    assert TaskGuard.read_status()["busy"] is False
    lease = TaskGuard.lease(
        kind="tag_run",
        job_id="j1",
        resource_key="a",
        label="demo",
    )
    with lease:
        st = TaskGuard.read_status()
        assert st["busy"] is True
        assert st["job_id"] == "j1"
        assert lease_file.is_file()
    assert TaskGuard.read_status()["busy"] is False


def test_second_acquire_raises(lease_file: Path):
    with TaskGuard.lease(kind="tag_run", job_id="j1", resource_key="a"):
        with pytest.raises(TaskLeaseBusyError):
            TaskGuard.lease(
                kind="strategy_run", job_id="j2", resource_key="b"
            ).acquire()


def test_context_manager_clears_busy(lease_file: Path):
    with TaskGuard.lease(kind="tag_run", job_id="j1", resource_key="a"):
        assert TaskGuard.read_status()["busy"] is True
    assert TaskGuard.read_status()["busy"] is False


def test_dead_holder_is_cleared_on_read(lease_file: Path):
    lease_file.write_text(
        json.dumps(
            {
                "kind": "strategy_attribute",
                "job_id": "attr-run-dead",
                "pid": 2**22,
                "label": "strategy_attribute:rsi_v3:price",
            }
        ),
        encoding="utf-8",
    )
    status = TaskGuard.read_status()
    assert status["busy"] is False
    assert lease_file.is_file() is False


def test_lease_without_pid_is_cleared(lease_file: Path):
    lease_file.write_text(
        json.dumps({"kind": "strategy_attribute", "job_id": "attr-run-old"}),
        encoding="utf-8",
    )
    assert TaskGuard.read_status()["busy"] is False
    lease = TaskGuard.lease(kind="strategy_attribute", job_id="j-new", resource_key="rsi_v3")
    lease.acquire()
    try:
        raw = json.loads(lease_file.read_text(encoding="utf-8"))
        assert raw["pid"] == os.getpid()
        assert raw["job_id"] == "j-new"
    finally:
        lease.release()
