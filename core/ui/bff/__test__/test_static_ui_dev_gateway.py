"""BFF 开发网关模式：不挂载 fed/build。"""

from __future__ import annotations

import pytest

from core.ui.bff.app import create_app
from core.ui.bff.static_ui import should_mount_fed_build, ui_dev_gateway_mode


@pytest.mark.parametrize("value", ("1", "true", "yes"))
def test_ui_dev_gateway_mode_truthy(monkeypatch, value: str) -> None:
    monkeypatch.setenv("NTQ_UI_DEV", value)
    assert ui_dev_gateway_mode() is True
    assert should_mount_fed_build() is False


def test_ui_dev_gateway_skips_fed_mount(monkeypatch) -> None:
    monkeypatch.setenv("NTQ_UI_DEV", "1")
    app = create_app()
    client = app.test_client()
    resp = client.get("/strategy-design")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    assert "BFF API" in data.get("message", "")
