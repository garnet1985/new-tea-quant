"""Tests for SetupTrace.install_complete."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.infra.trace import Trace  # noqa: F401 — ensure package importable for patch
from setup.core.trace_events import SetupTrace

pytestmark = pytest.mark.force_run


def test_install_complete_success_body() -> None:
    mock_trace = MagicMock()
    with patch("core.infra.trace.Trace", mock_trace):
        SetupTrace.install_complete(success=True, entry="cli")

    mock_trace.track.assert_called_once_with(
        "install.complete",
        {"success": True, "entry": "cli"},
    )
    mock_trace.send.assert_not_called()
    mock_trace.flush.assert_not_called()


def test_install_complete_failure_includes_error_code() -> None:
    mock_trace = MagicMock()
    with patch("core.infra.trace.Trace", mock_trace):
        SetupTrace.install_complete(
            success=False,
            entry="ui",
            error_code="pip_bff",
        )

    mock_trace.track.assert_called_once_with(
        "install.complete",
        {"success": False, "entry": "ui", "error_code": "pip_bff"},
    )


def test_install_complete_swallows_trace_errors() -> None:
    mock_trace = MagicMock()
    mock_trace.track.side_effect = RuntimeError("boom")
    with patch("core.infra.trace.Trace", mock_trace):
        SetupTrace.install_complete(success=True, entry="ui")  # must not raise
