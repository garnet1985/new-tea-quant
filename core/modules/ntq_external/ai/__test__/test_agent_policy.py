"""agent_policy 门面：框架态 / 产品态（不联网，用 fixture 或 monkeypatch）。"""

from __future__ import annotations

import pytest

from core.modules.ntq_external.ai import agent_policy as ap

pytestmark = pytest.mark.force_run


@pytest.fixture(autouse=True)
def _clear_cache():
    ap.clear_agent_policy_cache()
    yield
    ap.clear_agent_policy_cache()


def test_framework_when_no_token(monkeypatch):
    monkeypatch.setattr(ap, "member_token", lambda: None)
    out = ap.resolve_agent_policy()
    assert out["mode"] == "framework"
    assert out["ok"] is True
    assert out["sections"] is None
    assert out["reason"] == "missing_credential"


def test_product_fixture_when_token(monkeypatch):
    monkeypatch.setattr(ap, "member_token", lambda: "test-token")
    monkeypatch.setenv("NTQ_AGENT_POLICY_FIXTURE", "1")
    out = ap.resolve_agent_policy()
    assert out["mode"] == "product"
    assert out["ok"] is True
    assert out["version"] == "fixture-1"
    assert "远端产品准则 fixture" in out["sections"]["redlines"]
    assert "advice_head" in out["sections"]["replies"]


def test_product_fetch_failure(monkeypatch):
    monkeypatch.setattr(ap, "member_token", lambda: "test-token")
    monkeypatch.delenv("NTQ_AGENT_POLICY_FIXTURE", raising=False)
    monkeypatch.setattr(
        ap,
        "fetch_agent_policy",
        lambda **kwargs: {"ok": False, "error": "boom"},
    )
    out = ap.resolve_agent_policy(force_refresh=True)
    assert out["mode"] == "product"
    assert out["ok"] is False
    assert out["reason"] == "fetch_failed"
    assert "boom" in out["error"]


def test_cache_accelerates_second_resolve(monkeypatch):
    monkeypatch.setattr(ap, "member_token", lambda: "test-token")
    monkeypatch.setenv("NTQ_AGENT_POLICY_FIXTURE", "1")
    calls = {"n": 0}
    real = ap.fetch_agent_policy

    def counting(**kwargs):
        calls["n"] += 1
        return real(**kwargs)

    monkeypatch.setattr(ap, "fetch_agent_policy", counting)
    first = ap.resolve_agent_policy(force_refresh=True)
    second = ap.resolve_agent_policy()
    assert first["ok"] and second["ok"]
    assert calls["n"] == 1


def test_normalize_requires_redlines():
    bad = ap.normalize_policy_payload({"version": "1", "sections": {}})
    assert bad["ok"] is False
    good = ap.normalize_policy_payload(
        {"version": "1", "sections": {"redlines": "rule"}}
    )
    assert good["ok"] is True
    assert good["sections"]["redlines"] == "rule"
