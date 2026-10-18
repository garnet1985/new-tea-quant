"""设置页装载通用凭证：写入 userspace 文件，响应不含明文。"""

from __future__ import annotations

import pytest

from core.infra.project_context.core.path_manager import PathManager

pytestmark = pytest.mark.force_run

TOKEN = "ntq_" + "ab" * 24


@pytest.fixture
def token_file(tmp_path, monkeypatch):
    path = tmp_path / "membership_token.txt"
    monkeypatch.setattr(PathManager, "get_membership_token_file", staticmethod(lambda: path))
    return path


def test_membership_roundtrip_hides_token(token_file):
    from core.bff.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        empty = client.get("/api/v1/settings/membership")
        assert empty.status_code == 200
        body = empty.get_json()["message"]
        assert body["configured"] is False
        assert body["invalid"] is False
        assert TOKEN not in empty.get_data(as_text=True)

        guest = client.get("/api/v1/membership/profile")
        assert guest.status_code == 200
        profile = guest.get_json()["message"]
        assert profile["signed_in"] is False
        assert profile["reason"] == "missing"
        assert profile["register_url"].endswith("/zh-hans/user/register")
        assert TOKEN not in guest.get_data(as_text=True)

        bad = client.put("/api/v1/settings/membership", json={"token": "sk-vendor"})
        assert bad.status_code == 400
        assert "凭证格式不对" in bad.get_json()["message"]["detail"]
        assert not token_file.exists()

        saved = client.put("/api/v1/settings/membership", json={"token": TOKEN})
        assert saved.status_code == 200
        assert saved.get_json()["message"]["configured"] is True
        assert TOKEN not in saved.get_data(as_text=True)
        assert token_file.read_text(encoding="utf-8").strip() == TOKEN
        assert token_file.stat().st_mode & 0o777 == 0o600

        cleared = client.delete("/api/v1/settings/membership")
        assert cleared.status_code == 200
        assert cleared.get_json()["message"]["configured"] is False
        assert not token_file.exists()
