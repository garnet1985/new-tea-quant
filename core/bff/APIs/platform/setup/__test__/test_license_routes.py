"""安装条款接口：同意写入 .ntq，拒绝只安排退出。"""

from __future__ import annotations

import json

import pytest

import core.infra.setup.core.license_acceptance as lic

pytestmark = pytest.mark.force_run


@pytest.fixture(autouse=True)
def _no_trace_side_effect(monkeypatch):
    monkeypatch.setattr(lic, "apply_trace_consent", lambda: None)


@pytest.fixture
def acceptance_file(tmp_path, monkeypatch):
    path = tmp_path / "license_acceptance.json"
    monkeypatch.setattr(lic, "acceptance_path", lambda: path)
    return path


def test_accept_writes_revision_and_decline_does_not(acceptance_file, monkeypatch):
    from core.bff.app import create_app

    from core.infra.setup import Setup

    exited = []
    monkeypatch.setattr(lic, "exit_process_soon", lambda: exited.append(True))
    monkeypatch.setattr(Setup.trace, "app_start", staticmethod(lambda **_kwargs: None))
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        status = client.get("/api/v1/setup/license")
        assert status.status_code == 200
        assert status.get_json()["message"]["accepted"] is False
        assert status.get_json()["message"]["disclaimer_url"] == lic.DISCLAIMER_URL

        declined = client.post("/api/v1/setup/license/decline")
        assert declined.status_code == 200
        assert declined.get_json()["message"]["exiting"] is True
        assert exited == [True]
        assert acceptance_file.exists() is False

        accepted = client.post("/api/v1/setup/license/accept")
        assert accepted.status_code == 200
        assert accepted.get_json()["message"]["accepted"] is True
        saved = json.loads(acceptance_file.read_text(encoding="utf-8"))
        assert saved["revision"] == lic.LICENSE_REVISION
        assert saved["source"] == "ui"
