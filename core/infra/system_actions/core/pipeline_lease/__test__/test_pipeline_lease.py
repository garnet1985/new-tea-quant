"""Tests for global pipeline lease (via Facade + 实现类)。"""

from __future__ import annotations

import pytest

from core.infra.system_actions import SystemActions
from core.infra.system_actions.contracts import PipelineLeaseBusyError

pytestmark = pytest.mark.force_run


@pytest.fixture
def isolated_lease(tmp_path, monkeypatch):
    lease_file = tmp_path / "pipeline_active.json"
    monkeypatch.setattr(
        "core.infra.system_actions.core.pipeline_lease.pipeline_lease.PipelineLease.lease_path",
        staticmethod(lambda: lease_file),
    )
    return lease_file


def test_read_idle_when_missing(isolated_lease):
    assert SystemActions.pipeline.read_status()["busy"] is False


def test_acquire_and_release(isolated_lease):
    lease = SystemActions.pipeline.lease(
        kind="tag_run",
        job_id="tag-run-abc",
        resource_key="demo/x",
        domains=["data", "tag"],
    )
    lease.acquire()
    assert isolated_lease.is_file()
    st = SystemActions.pipeline.read_status()
    assert st["busy"] is True
    assert st["kind"] == "tag_run"
    assert st["job_id"] == "tag-run-abc"
    lease.release()
    assert not isolated_lease.exists()
    assert SystemActions.pipeline.read_status()["busy"] is False


def test_second_acquire_raises(isolated_lease):
    with SystemActions.pipeline.lease(kind="tag_run", job_id="j1", resource_key="a"):
        with pytest.raises(PipelineLeaseBusyError):
            SystemActions.pipeline.lease(
                kind="data_renew", job_id="j2", resource_key="b"
            ).acquire()


def test_context_manager_releases(isolated_lease):
    with SystemActions.pipeline.lease(kind="tag_run", job_id="j1", resource_key="a"):
        assert SystemActions.pipeline.read_status()["busy"] is True
    assert SystemActions.pipeline.read_status()["busy"] is False
