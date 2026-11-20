"""会员邮件额度：凭证只用于请求，不出现在返回里。"""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from core.infra.project_context.core.path_manager import PathManager

pytestmark = pytest.mark.force_run

TOKEN = "ntq_" + "ef" * 24


@pytest.fixture
def token_file(tmp_path, monkeypatch):
    path = tmp_path / "membership_token.txt"
    path.write_text(TOKEN + "\n", encoding="utf-8")
    monkeypatch.setattr(PathManager, "get_membership_token_file", staticmethod(lambda: path))
    return path


def test_missing_token_still_returns_policy(tmp_path, monkeypatch):
    path = tmp_path / "missing.txt"
    monkeypatch.setattr(PathManager, "get_membership_token_file", staticmethod(lambda: path))
    from core.modules.ntq_external.member_mail_quota import member_mail_quota

    body = member_mail_quota()
    assert body["available"] is False
    assert body["reason"] == "missing"
    assert "终身共可发" in body["policy"]
    assert "注册邮箱" in body["policy"]
    assert "80" in body["policy"]
    assert TOKEN not in json.dumps(body)


def test_rejected_token(token_file, monkeypatch):
    def raise_unauthorized(request, timeout=8):
        raise urllib.error.HTTPError(
            request.full_url,
            401,
            "unauthorized",
            hdrs=None,
            fp=io.BytesIO(b"{}"),
        )

    monkeypatch.setattr("urllib.request.urlopen", raise_unauthorized)
    from core.modules.ntq_external.member_mail_quota import member_mail_quota

    body = member_mail_quota()
    assert body["available"] is False
    assert body["reason"] == "rejected"
    assert "终身共可发" in body["policy"]


def test_quota_ok(token_file, monkeypatch):
    payload = {"limit": 30, "used": 7, "remaining": 23, "unlimited": False}

    class _Resp:
        status = 200

        def read(self):
            return json.dumps(payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    seen = {}

    def fake_urlopen(request, timeout=8):
        seen["auth"] = request.get_header("Authorization")
        seen["url"] = request.full_url
        return _Resp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    from core.modules.ntq_external.member_mail_quota import member_mail_quota

    body = member_mail_quota()
    assert body["available"] is True
    assert body["limit"] == 30
    assert body["used"] == 7
    assert body["remaining"] == 23
    assert body["unlimited"] is False
    assert seen["auth"] == f"Bearer {TOKEN}"
    assert seen["url"].endswith("/api/v1/ntq-mail/quota")
    assert TOKEN not in json.dumps(body)


def test_quota_unlimited(token_file, monkeypatch):
    payload = {"limit": None, "used": 2, "remaining": None, "unlimited": True}

    class _Resp:
        status = 200

        def read(self):
            return json.dumps(payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: _Resp())
    from core.modules.ntq_external.member_mail_quota import member_mail_quota

    body = member_mail_quota()
    assert body["available"] is True
    assert body["unlimited"] is True
    assert body["remaining"] is None
