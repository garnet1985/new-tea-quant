"""Tests for TaskLease mutual exclusion."""

from __future__ import annotations

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
