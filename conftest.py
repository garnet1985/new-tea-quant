"""Project-wide pytest hooks.

Refactor freeze has been lifted: tests run by default.

Environment-dependent or intentionally deferred cases should use
``pytest.mark.skip`` / ``skipif`` with an explicit reason (missing
tools/data on CI, STALE API, etc.).
"""
from __future__ import annotations

import pytest


class TraceHttpBlock:
    """pytest 下 Trace 上报一律视为成功，不打真实网络。"""

    @staticmethod
    def post(*args, **kwargs) -> bool:
        return True


class FeedbackHttpBlock:
    """pytest 下 Feedback 上报一律视为成功，不打真实网络。"""

    @staticmethod
    def post(*args, **kwargs) -> bool:
        return True


def pytest_configure(config: pytest.Config) -> None:
    # Kept for backward compatibility with existing ``force_run`` markers.
    config.addinivalue_line(
        "markers",
        "force_run: historical opt-in during refactor freeze (no longer required)",
    )


@pytest.fixture(autouse=True)
def ntq_block_trace_http(monkeypatch: pytest.MonkeyPatch) -> None:
    # Import concrete modules first: dotted-path setattr fails when the
    # ``services`` package is not yet loaded under ``core.infra.trace.core``.
    from core.infra.feedback.core.services import client_service as feedback_client
    from core.infra.trace.core.services import client_service as trace_client

    monkeypatch.setattr(
        trace_client.TraceClientService,
        "post",
        staticmethod(TraceHttpBlock.post),
    )
    monkeypatch.setattr(
        feedback_client.FeedbackClientService,
        "post",
        staticmethod(FeedbackHttpBlock.post),
    )
