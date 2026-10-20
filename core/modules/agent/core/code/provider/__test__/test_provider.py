"""Provider：ntq | 某一个自备，一个 id 干到底。"""

from __future__ import annotations

from core.modules.agent.core.code.provider import provider as provider_mod
from core.modules.agent.core.code.provider.provider import resolve_provider


def test_own_explicit(monkeypatch):
    monkeypatch.delenv("NTQ_AGENT_OWN_KEYS", raising=False)
    monkeypatch.setattr(
        provider_mod, "_local_key_ready", lambda pid: pid == "openai"
    )
    p = resolve_provider("openai")
    assert p.id == "openai"
    assert p.available
    assert not p.is_ntq


def test_own_missing_key(monkeypatch):
    monkeypatch.delenv("NTQ_AGENT_OWN_KEYS", raising=False)
    monkeypatch.setattr(provider_mod, "_local_key_ready", lambda pid: False)
    p = resolve_provider("openai")
    assert not p.available


def test_ntq_needs_membership(monkeypatch):
    monkeypatch.delenv("NTQ_AGENT_OWN_KEYS", raising=False)
    monkeypatch.setattr(provider_mod, "_membership_ready", lambda: False)
    p = resolve_provider(None)
    assert p.id == "ntq"
    assert not p.available


def test_ntq_ok_with_membership(monkeypatch):
    monkeypatch.delenv("NTQ_AGENT_OWN_KEYS", raising=False)
    monkeypatch.setattr(provider_mod, "_membership_ready", lambda: True)
    p = resolve_provider(None)
    assert p.is_ntq
    assert p.available
    assert p.id == "ntq"


def test_dev_own_keys_single_provider(monkeypatch):
    monkeypatch.setenv("NTQ_AGENT_OWN_KEYS", "1")
    monkeypatch.setattr(
        provider_mod, "_local_key_ready", lambda pid: pid == "deepseek"
    )
    p = resolve_provider(None)
    assert p.id == "deepseek"
    assert p.available
    assert not p.is_ntq
