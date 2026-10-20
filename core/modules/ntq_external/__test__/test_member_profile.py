"""官网会员条：凭证只用于请求，不出现在返回里。"""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from core.infra.project_context.core.path_manager import PathManager

pytestmark = pytest.mark.force_run

TOKEN = "ntq_" + "cd" * 24


@pytest.fixture
def token_file(tmp_path, monkeypatch):
    path = tmp_path / "membership_token.txt"
    path.write_text(TOKEN + "\n", encoding="utf-8")
    monkeypatch.setattr(PathManager, "get_membership_token_file", staticmethod(lambda: path))
    return path


def test_missing_token_offers_register(tmp_path, monkeypatch):
    path = tmp_path / "missing.txt"
    monkeypatch.setattr(PathManager, "get_membership_token_file", staticmethod(lambda: path))
    from core.modules.ntq_external.member_profile import member_profile

    body = member_profile()
    assert body["signed_in"] is False
    assert body["reason"] == "missing"
    assert body["register_url"].endswith("/zh-hans/user/register")
    assert TOKEN not in json.dumps(body)


def test_rejected_token_offers_register(token_file, monkeypatch):
    def raise_unauthorized(request, timeout=8):
        raise urllib.error.HTTPError(
            request.full_url,
            401,
            "unauthorized",
            hdrs=None,
            fp=io.BytesIO(b"{}"),
        )

    monkeypatch.setattr("urllib.request.urlopen", raise_unauthorized)
    from core.modules.ntq_external import member_profile as module

    body = module.member_profile()
    assert body["signed_in"] is False
    assert body["reason"] == "rejected"
    assert TOKEN not in json.dumps(body)


def test_profile_returns_name_avatar_points(token_file, monkeypatch):
    seen = {}

    class Response:
        status = 200

        def read(self):
            return json.dumps({
                "name": "青茶",
                "avatar": "https://www.new-tea.cn/files/a.png",
                "points": 500,
                "tier": "standard",
                "is_pro": False,
                "catfood": 500.0,
                "token_balance": 5000000,
                "currency": "猫粮",
                "sync_access": "demo",
            }).encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_open(request, timeout=8):
        seen["auth"] = request.get_header("Authorization")
        seen["timeout"] = timeout
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_open)
    from core.modules.ntq_external.member_profile import member_profile

    body = member_profile()
    assert seen["auth"] == f"Bearer {TOKEN}"
    assert body == {
        "signed_in": True,
        "register_url": body["register_url"],
        "name": "青茶",
        "avatar": "https://www.new-tea.cn/files/a.png",
        "points": 500,
        "tier": "standard",
        "is_pro": False,
        "catfood": 500.0,
        "token_balance": 5000000,
        "currency": "猫粮",
        "sync_access": "demo",
        "reason": None,
    }
    assert TOKEN not in json.dumps(body)
