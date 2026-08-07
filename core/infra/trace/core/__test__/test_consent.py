"""Consent gating tests: tracing is opt-in and defaults to off."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.force_run


@pytest.fixture()
def consent_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    config_root = tmp_path / "userspace" / "system" / "config"
    config_root.mkdir(parents=True)

    monkeypatch.delenv("NTQ_TRACE_ENABLED", raising=False)
    monkeypatch.delenv("NTQ_TRACE_SKIP", raising=False)

    from core.infra.trace.core.services import consent_service

    monkeypatch.setattr(
        consent_service.TraceConsentService,
        "consent_path",
        staticmethod(lambda: config_root / "trace_consent.json"),
    )
    return config_root


def test_disabled_when_never_asked(consent_env: Path) -> None:
    from core.infra.trace.core.services.config_service import TraceConfigService
    from core.infra.trace.core.services.consent_service import TraceConsentService

    assert TraceConsentService.is_decided() is False
    assert TraceConsentService.is_granted() is False
    assert TraceConfigService.is_enabled() is False


def test_grant_and_revoke(consent_env: Path) -> None:
    from core.infra.trace.core.services.config_service import TraceConfigService
    from core.infra.trace.core.services.consent_service import TraceConsentService

    assert TraceConsentService.grant(source="cli") is True
    assert (consent_env / "trace_consent.json").is_file()
    assert TraceConsentService.is_decided() is True
    assert TraceConfigService.is_enabled() is True

    assert TraceConsentService.revoke(source="ui") is True
    assert TraceConsentService.is_decided() is True
    assert TraceConsentService.is_granted() is False
    assert TraceConfigService.is_enabled() is False


def test_track_is_noop_without_consent(
    consent_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core.infra.trace import Trace
    from core.infra.trace.core.services import queue_service

    enqueued = []
    monkeypatch.setattr(
        queue_service.TraceQueueService,
        "enqueue",
        staticmethod(lambda event, **kwargs: enqueued.append(event) or True),
    )

    Trace.track("install.complete", {"success": True})
    assert enqueued == []

    Trace.consent.grant(source="test")
    Trace.track("install.complete", {"success": True})
    assert len(enqueued) == 1


def test_skip_env_overrides_consent(
    consent_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core.infra.trace.core.services.config_service import TraceConfigService
    from core.infra.trace.core.services.consent_service import TraceConsentService

    TraceConsentService.grant(source="test")
    monkeypatch.setenv("NTQ_TRACE_SKIP", "1")
    assert TraceConfigService.is_enabled() is False


def test_malformed_consent_file_is_treated_as_undecided(consent_env: Path) -> None:
    from core.infra.trace.core.services.consent_service import TraceConsentService

    (consent_env / "trace_consent.json").write_text("{not json", encoding="utf-8")
    assert TraceConsentService.is_decided() is False
    assert TraceConsentService.is_granted() is False
