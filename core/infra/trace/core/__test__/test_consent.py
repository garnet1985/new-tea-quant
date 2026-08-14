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

    from core.infra.trace.core.services import client_service, consent_service

    monkeypatch.setattr(
        consent_service.TraceConsentService,
        "consent_path",
        staticmethod(lambda: config_root / "trace_consent.json"),
    )
    # Default: never POST to the production endpoint from consent tests.
    # Individual tests may replace this with a capturing fake_post.
    monkeypatch.setattr(
        client_service.TraceClientService,
        "post",
        staticmethod(lambda *args, **kwargs: True),
    )
    return config_root


def test_disabled_when_never_asked(consent_env: Path) -> None:
    from core.infra.trace.core.services.config_service import TraceConfigService
    from core.infra.trace.core.services.consent_service import TraceConsentService

    assert TraceConsentService.is_decided() is False
    assert TraceConsentService.is_granted() is False
    assert TraceConfigService.is_enabled() is False


def test_grant_and_revoke(
    consent_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core.infra.trace.core.services import client_service
    from core.infra.trace.core.services.config_service import TraceConfigService
    from core.infra.trace.core.services.consent_service import TraceConsentService

    # grant/revoke always emit track.decision; never hit the real endpoint in tests.
    monkeypatch.setattr(
        client_service.TraceClientService,
        "post",
        staticmethod(lambda *args, **kwargs: True),
    )

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
    from core.infra.trace.contracts import TraceEvent
    from core.infra.trace.core.services import client_service, queue_service

    posts = []
    enqueued = []

    def fake_post(url, event, *, timeout_sec):
        posts.append(event.to_wire_dict() if isinstance(event, TraceEvent) else event)
        return True

    monkeypatch.setattr(
        client_service.TraceClientService,
        "post",
        staticmethod(fake_post),
    )
    monkeypatch.setattr(
        queue_service.TraceQueueService,
        "enqueue",
        staticmethod(lambda event, **kwargs: enqueued.append(event) or True),
    )

    Trace.track("install.complete", {"success": True})
    assert posts == []
    assert enqueued == []

    Trace.consent.grant(source="test")
    assert len(posts) == 1
    assert posts[0]["event"] == "track.decision"
    assert enqueued == []

    Trace.track("install.complete", {"success": True})
    assert len(posts) == 2
    assert posts[1]["event"] == "install.complete"
    assert enqueued == []


def test_queue_enqueues_with_consent(
    consent_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core.infra.trace import Trace
    from core.infra.trace.contracts import TraceEvent
    from core.infra.trace.core.services import client_service, queue_service

    posts = []
    enqueued = []

    def fake_post(url, event, *, timeout_sec):
        posts.append(event.to_wire_dict() if isinstance(event, TraceEvent) else event)
        return True

    monkeypatch.setattr(
        client_service.TraceClientService,
        "post",
        staticmethod(fake_post),
    )
    monkeypatch.setattr(
        queue_service.TraceQueueService,
        "enqueue",
        staticmethod(lambda event, **kwargs: enqueued.append(event) or True),
    )

    Trace.consent.grant(source="test")
    assert len(posts) == 1
    assert posts[0]["event"] == "track.decision"
    assert enqueued == []

    Trace.queue("install.complete", {"success": True})
    assert len(enqueued) == 1
    assert enqueued[0].event == "install.complete"


def test_grant_emits_track_decision(
    consent_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core.infra.trace import Trace
    from core.infra.trace.core.services import client_service

    posts = []

    def fake_post(url, event, *, timeout_sec):
        from core.infra.trace.contracts import TraceEvent

        posts.append(event.to_wire_dict() if isinstance(event, TraceEvent) else event)
        return True

    monkeypatch.setattr(
        client_service.TraceClientService, "post", staticmethod(fake_post)
    )

    assert Trace.consent.grant(source="cli_install") is True
    assert len(posts) == 1
    assert posts[0]["event"] == "track.decision"
    assert posts[0]["body"] == {"enabled": True, "source": "cli_install"}


def test_revoke_emits_track_decision_even_when_disabled(
    consent_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core.infra.trace import Trace
    from core.infra.trace.core.services import client_service

    posts = []

    def fake_post(url, event, *, timeout_sec):
        from core.infra.trace.contracts import TraceEvent

        posts.append(event.to_wire_dict() if isinstance(event, TraceEvent) else event)
        return True

    monkeypatch.setattr(
        client_service.TraceClientService, "post", staticmethod(fake_post)
    )

    Trace.consent.grant(source="cli")
    posts.clear()
    assert Trace.consent.revoke(source="ui") is True
    assert len(posts) == 1
    assert posts[0]["event"] == "track.decision"
    assert posts[0]["body"] == {"enabled": False, "source": "ui"}


def test_ask_noop_does_not_reemit_decision(
    consent_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core.infra.trace import Trace
    from core.infra.trace.core.services import client_service, permission_service

    posts = []

    def fake_post(url, event, *, timeout_sec):
        from core.infra.trace.contracts import TraceEvent

        posts.append(event.to_wire_dict() if isinstance(event, TraceEvent) else event)
        return True

    monkeypatch.setattr(
        client_service.TraceClientService, "post", staticmethod(fake_post)
    )
    monkeypatch.setattr(
        permission_service.TracePermissionService,
        "_can_prompt",
        staticmethod(lambda: True),
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": "y")

    assert Trace.ask_permission(source="cli") is True
    assert sum(1 for p in posts if p["event"] == "track.decision") == 1

    posts.clear()
    assert Trace.ask_permission(source="cli") is True
    assert posts == []

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
