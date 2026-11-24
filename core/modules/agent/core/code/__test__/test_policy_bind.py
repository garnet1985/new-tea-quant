"""准则绑定：框架态本地 md；远端注入由官网负责（本机不硬拒）。"""

from __future__ import annotations

import pytest

from core.modules.agent.core.code.executor.shared.prompt_common import product_identity_text
from core.modules.agent.core.code.executor.shared.prompt_loader import load_reply
from core.modules.agent.core.code.policy_bind import policy_sections_scope
from core.modules.ntq_external.ai import agent_policy as ap

pytestmark = pytest.mark.force_run


@pytest.fixture(autouse=True)
def _clear_policy_cache():
    ap.clear_agent_policy_cache()
    yield
    ap.clear_agent_policy_cache()


def test_framework_identity_uses_local_md(monkeypatch):
    monkeypatch.setattr(ap, "member_token", lambda: None)
    out = ap.resolve_agent_policy()
    assert out["mode"] == "framework"
    with policy_sections_scope(None):
        text = product_identity_text()
    assert "New Tea Quant" in text


def test_optional_remote_sections_still_inject_locally(monkeypatch):
    """本机仍可选用远端 sections；安全边界在官网 chat 注入，不依赖此路径。"""
    monkeypatch.setattr(ap, "member_token", lambda: "tok")
    monkeypatch.setenv("NTQ_AGENT_POLICY_FIXTURE", "1")
    resolved = ap.resolve_agent_policy(force_refresh=True)
    assert resolved["ok"] is True
    with policy_sections_scope(resolved["sections"]):
        text = product_identity_text()
        assert "远端产品准则 fixture" in text
        assert "【远端准则】" in load_reply("advice_head")


def test_product_fetch_fail_does_not_block_local_identity(monkeypatch):
    """拉 policy 失败不再硬拒 Agent；框架/本地文案仍可用。"""
    monkeypatch.setattr(ap, "member_token", lambda: "tok")
    monkeypatch.delenv("NTQ_AGENT_POLICY_FIXTURE", raising=False)
    monkeypatch.setattr(
        ap,
        "fetch_agent_policy",
        lambda **kwargs: {"ok": False, "error": "net down"},
    )
    out = ap.resolve_agent_policy(force_refresh=True)
    assert out["mode"] == "product"
    assert out["ok"] is False
    with policy_sections_scope(None):
        assert "New Tea Quant" in product_identity_text()
