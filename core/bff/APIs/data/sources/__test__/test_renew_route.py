"""数据源更新接口：不在测试里真的去拉官网。"""

from __future__ import annotations

import pytest

from core.bff.app import create_app
from core.infra.task_guard import TaskGuard

pytestmark = pytest.mark.force_run


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_renew_route_starts_without_calling_remote(client, monkeypatch):
    from core.bff.APIs.data.sources import routes

    seen = {}

    def fake_trigger(source=None):
        seen["source"] = source
        return {
            "is_triggered": True,
            "job_id": "data-renew-test",
            "source": source or "",
            "running": True,
        }

    monkeypatch.setattr(routes.DataRenewLauncher, "trigger", staticmethod(fake_trigger))
    started = client.post("/api/v1/data-sources/renew", json={})
    assert started.status_code == 200
    assert started.get_json()["message"]["job_id"] == "data-renew-test"
    assert seen["source"] is None

    one = client.post("/api/v1/data-sources/renew", json={"source": "cpi"})
    assert one.status_code == 200
    assert seen["source"] == "cpi"


def test_launcher_refuses_when_another_task_is_busy(monkeypatch):
    from core.bff.APIs.data.sources.renew_launcher import DataRenewLauncher

    monkeypatch.setattr(
        TaskGuard,
        "read_status",
        staticmethod(lambda: {"busy": True, "kind": "tag_run"}),
    )
    body = DataRenewLauncher.trigger(None)
    assert body["is_triggered"] is False
    assert "tag_run" in body["reason"]


def test_public_progress_uses_the_running_source(tmp_path, monkeypatch):
    monkeypatch.setenv("NTQ_PROGRESS_DIR", str(tmp_path))
    monkeypatch.setenv("NTQ_PROGRESS_FLUSH_DELAY", "0")
    from core.bff.APIs.data.sources.renew_launcher import _public_progress
    from core.infra.progress import Progress
    from core.infra.progress.core import store

    store.reset()
    Progress.start(
        "data-renew-abc",
        job="renew",
        label="更新数据",
        steps=[
            {"id": "data-renew-abc:cpi", "label": "cpi"},
            {"id": "data-renew-abc:list", "label": "stock_list"},
        ],
    )
    Progress.finish("data-renew-abc:cpi")
    Progress.tick(
        "data-renew-abc:list",
        2,
        8,
        source="stock_list",
        detail="第 2 页",
        log=False,
    )

    body = _public_progress()
    assert body["step"] == 1
    assert body["step_total"] == 2
    assert body["source"] == "stock_list"
    assert body["sub"] == 2
    assert body["sub_total"] == 8
    assert body["detail"] == "第 2 页"
    assert body["ratio"] == 0.625
    Progress.clear("data-renew-abc")
    assert _public_progress()["step_total"] == 0
    store.reset()
