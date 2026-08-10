"""Unit tests for sanitize / queue / send / track (mocked HTTP)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Union

import pytest

from core.infra.trace.contracts import TraceEvent

pytestmark = pytest.mark.force_run


@pytest.fixture()
def trace_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    userspace = tmp_path / "userspace"
    ntq = userspace / ".ntq"
    ntq.mkdir(parents=True)

    monkeypatch.setenv("NTQ_TRACE_ENABLED", "1")
    monkeypatch.delenv("NTQ_TRACE_SKIP", raising=False)

    from core.infra.trace.contracts import TraceConfig
    from core.infra.trace.core.services import (
        config_service,
        identity_service,
        queue_service,
        track_service,
    )

    def _dirs():
        q = ntq / "trace" / "queue"
        inflight = ntq / "trace" / "inflight"
        q.mkdir(parents=True, exist_ok=True)
        inflight.mkdir(parents=True, exist_ok=True)
        return ntq / "trace", q, inflight

    monkeypatch.setattr(queue_service.TraceQueueService, "_dirs", staticmethod(_dirs))
    monkeypatch.setattr(
        config_service.TraceConfigService,
        "load",
        staticmethod(
            lambda: TraceConfig(
                enabled=True,
                target_url="https://example.test/api/v1/traces",
                timeout_sec=0.5,
                queue_max=3,
                extreme_depth=2,
                max_attempts=3,
                body_max_bytes=4096,
                bff_drain_interval_sec=60,
            )
        ),
    )
    monkeypatch.setattr(
        identity_service.TraceIdentityService,
        "get_or_create",
        staticmethod(lambda: "ntq_i_" + "a" * 32),
    )
    monkeypatch.setattr(
        track_service.TraceIdentityService,
        "get_or_create",
        staticmethod(lambda: "ntq_i_" + "a" * 32),
    )
    return ntq


def test_sanitize_body_allows_flexible_fields() -> None:
    from core.infra.trace.core.services.sanitize_service import TraceSanitizeService

    out = TraceSanitizeService.body(
        {
            "success": True,
            "msg": "deps failed",
            "error_code": "step_failed:resolve_deps",
            "token": "should-drop",
            "nested": {"ok": 1},
        }
    )
    assert out["success"] is True
    assert out["msg"] == "deps failed"
    assert "token" not in out
    assert out["nested"]["ok"] == 1


def test_sanitize_event_name() -> None:
    from core.infra.trace.core.services.sanitize_service import TraceSanitizeService

    assert TraceSanitizeService.event_name("install.complete") == "install.complete"
    assert TraceSanitizeService.event_name("../etc/passwd") is None
    assert TraceSanitizeService.event_name("") is None


def test_meta_excludes_ip_and_hostname() -> None:
    from core.infra.trace.core.services.sanitize_service import TraceSanitizeService

    out = TraceSanitizeService.meta(
        {"os": "darwin", "ip": "1.2.3.4", "hostname": "secret-pc", "python_version": "3.9"}
    )
    assert out == {"os": "darwin", "python_version": "3.9"}


def test_queue_drops_oldest(trace_dirs: Path) -> None:
    from core.infra.trace.core.services.queue_service import TraceQueueService

    for i in range(5):
        TraceQueueService.enqueue(
            TraceEvent(
                event_id=f"e{i}",
                installation_id="ntq_i_" + "a" * 32,
                event="t",
                occurred_at="2026-01-01T00:00:00Z",
            ),
            queue_max=3,
        )
    files = TraceQueueService.list_files()
    assert len(files) == 3


def test_queue_and_send_mocked(trace_dirs: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from core.infra.trace import Trace
    from core.infra.trace.core.services import client_service, queue_service

    calls = []

    def fake_post(
        url: str,
        event: Union[TraceEvent, Dict[str, Any]],
        *,
        timeout_sec: float,
    ) -> bool:
        if isinstance(event, TraceEvent):
            calls.append(event.to_wire_dict())
        else:
            calls.append(event)
        return True

    monkeypatch.setattr(client_service.TraceClientService, "post", staticmethod(fake_post))

    Trace.queue(
        "install.complete",
        {"success": True, "source": "manual_test", "secret": "x"},
    )
    assert queue_service.TraceQueueService.depth() == 1
    n = Trace.send(budget="standard")
    assert n == 1
    assert queue_service.TraceQueueService.depth() == 0
    assert calls and calls[0]["event"] == "install.complete"
    assert "secret" not in calls[0]["body"]
    assert "os" in calls[0]["meta"]
    assert calls[0]["body"].get("success") is True


def test_track_posts_immediately(trace_dirs: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from core.infra.trace import Trace
    from core.infra.trace.core.services import client_service, queue_service

    calls = []

    def fake_post(
        url: str,
        event: Union[TraceEvent, Dict[str, Any]],
        *,
        timeout_sec: float,
    ) -> bool:
        if isinstance(event, TraceEvent):
            calls.append(event.to_wire_dict())
        else:
            calls.append(event)
        return True

    monkeypatch.setattr(client_service.TraceClientService, "post", staticmethod(fake_post))

    Trace.track("install.complete", {"success": True, "secret": "x"})
    assert queue_service.TraceQueueService.depth() == 0
    assert calls and calls[0]["event"] == "install.complete"
    assert "secret" not in calls[0]["body"]
    assert calls[0]["body"].get("success") is True


def test_track_enqueues_when_post_fails(
    trace_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core.infra.trace import Trace
    from core.infra.trace.core.services import client_service, queue_service

    monkeypatch.setattr(
        client_service.TraceClientService,
        "post",
        staticmethod(lambda *a, **k: False),
    )

    Trace.track("install.complete", {"success": False, "error_code": "pip_bff"})
    assert queue_service.TraceQueueService.depth() == 1


def test_claim_atomic(trace_dirs: Path) -> None:
    from core.infra.trace.core.services.queue_service import TraceQueueService

    TraceQueueService.enqueue(
        TraceEvent(
            event_id="e1",
            installation_id="ntq_i_" + "a" * 32,
            event="t",
            occurred_at="2026-01-01T00:00:00Z",
        ),
        queue_max=10,
    )
    claimed = TraceQueueService.claim_next()
    assert claimed is not None
    path, event = claimed
    assert event.event_id == "e1"
    assert path.parent.name == "inflight"
    assert TraceQueueService.claim_next() is None
    TraceQueueService.complete(path)
