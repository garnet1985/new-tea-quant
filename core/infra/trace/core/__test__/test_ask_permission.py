"""Trace.ask_permission() tests."""

from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

pytestmark = pytest.mark.force_run


@pytest.fixture()
def consent_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    config_root = tmp_path / "userspace" / "system" / "config"
    config_root.mkdir(parents=True)

    from core.infra.trace.core.services import client_service, consent_service

    monkeypatch.setattr(
        consent_service.TraceConsentService,
        "consent_path",
        staticmethod(lambda: config_root / "trace_consent.json"),
    )
    monkeypatch.delenv("NTQ_TRACE_ENABLED", raising=False)
    monkeypatch.delenv("NTQ_TRACE_SKIP", raising=False)
    # grant/revoke emit track.decision; never hit production from unit tests.
    monkeypatch.setattr(
        client_service.TraceClientService,
        "post",
        staticmethod(lambda *args, **kwargs: True),
    )
    return config_root


def test_ask_grants_on_y(
    consent_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core.infra.trace import Trace
    from core.infra.trace.core.services import permission_service

    monkeypatch.setattr(
        permission_service.TracePermissionService,
        "_can_prompt",
        staticmethod(lambda: True),
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": "y")

    assert Trace.ask_permission(source="test") is True
    assert Trace.consent.is_decided() is True
    assert Trace.consent.is_granted() is True
    assert (consent_home / "trace_consent.json").is_file()


def test_ask_declines_on_enter(
    consent_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core.infra.trace import Trace
    from core.infra.trace.core.services import permission_service

    monkeypatch.setattr(
        permission_service.TracePermissionService,
        "_can_prompt",
        staticmethod(lambda: True),
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")

    assert Trace.ask_permission(source="test") is False
    assert Trace.consent.is_decided() is True
    assert Trace.consent.is_granted() is False


def test_ask_noop_when_already_decided(
    consent_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core.infra.trace import Trace

    Trace.consent.set(True, source="prior")
    calls: List[str] = []
    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt="": calls.append("hit") or "n",
    )

    assert Trace.ask_permission(source="test") is True
    assert calls == []
    assert Trace.consent.is_granted() is True


def test_ask_skips_non_tty(
    consent_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core.infra.trace import Trace
    from core.infra.trace.core.services import permission_service

    monkeypatch.setattr(
        permission_service.TracePermissionService,
        "_can_prompt",
        staticmethod(lambda: False),
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": "y")

    assert Trace.ask_permission(source="test") is False
    assert Trace.consent.is_decided() is False
    assert Trace.consent.needs_ask() is True
