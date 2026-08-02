"""Tests for global pipeline lease."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.force_run

from core.infra.system_actions.cache_cleanup.pipeline_lease import PipelineLease
from core.infra.system_actions.contracts import PipelineLeaseBusyError


@pytest.fixture
def isolated_lease(tmp_path, monkeypatch):
    lease_file = tmp_path / "pipeline_active.json"
    monkeypatch.setattr(
        "core.infra.system_actions.cache_cleanup.pipeline_lease._lease_path",
        lambda: lease_file,
    )
    return lease_file


def test_read_idle_when_missing(isolated_lease):
    assert PipelineLease.read_status()["busy"] is False


def test_acquire_and_release(isolated_lease):
    lease = PipelineLease(
        kind="tag_run",
        job_id="tag-run-abc",
        resource_key="demo/x",
        domains=["data", "tag"],
    )
    lease.acquire()
    assert isolated_lease.is_file()
    st = PipelineLease.read_status()
    assert st["busy"] is True
    assert st["kind"] == "tag_run"
    assert st["job_id"] == "tag-run-abc"
    lease.release()
    assert not isolated_lease.exists()
    assert PipelineLease.read_status()["busy"] is False


def test_second_acquire_raises(isolated_lease):
    with PipelineLease(kind="tag_run", job_id="j1", resource_key="a"):
        with pytest.raises(PipelineLeaseBusyError):
            PipelineLease(kind="data_renew", job_id="j2", resource_key="b").acquire()


def test_context_manager_releases(isolated_lease):
    with PipelineLease(kind="tag_run", job_id="j1", resource_key="a"):
        assert PipelineLease.read_status()["busy"] is True
    assert PipelineLease.read_status()["busy"] is False
