"""Tests for SetupTrace install events."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.infra.trace import Trace  # noqa: F401 — ensure package importable for patch
from core.infra.setup.core.trace_events import SetupTrace

pytestmark = pytest.mark.force_run


def test_install_complete_success_body() -> None:
    mock_trace = MagicMock()
    with patch("core.infra.trace.Trace", mock_trace):
        SetupTrace.install_complete(success=True, entry="cli")

    mock_trace.track_setup.assert_called_once_with(
        "install.complete",
        {"success": True, "entry": "cli"},
    )
    mock_trace.track.assert_not_called()


def test_install_complete_includes_step_timings() -> None:
    mock_trace = MagicMock()
    with patch("core.infra.trace.Trace", mock_trace):
        SetupTrace.install_complete(
            success=True,
            entry="ui",
            elapsed_seconds=91.234,
            step_seconds={"resolve_deps": 12.04, "resolve_ml_deps": 78.9},
            skipped=["import_data"],
        )

    name, body = mock_trace.track_setup.call_args.args
    assert name == "install.complete"
    assert body["elapsed_seconds"] == 91.23
    assert body["step_seconds"]["resolve_deps"] == 12.04
    assert body["step_seconds"]["resolve_ml_deps"] == 78.9
    assert body["skipped"] == ["import_data"]


def test_install_complete_failure_includes_error_code() -> None:
    mock_trace = MagicMock()
    with patch("core.infra.trace.Trace", mock_trace):
        SetupTrace.install_complete(
            success=False,
            entry="ui",
            error_code="pip_bff",
        )

    mock_trace.track_setup.assert_called_once_with(
        "install.complete",
        {"success": False, "entry": "ui", "error_code": "pip_bff"},
    )


def test_install_step_failed_includes_class_and_safe_message() -> None:
    mock_trace = MagicMock()
    with patch("core.infra.trace.Trace", mock_trace):
        SetupTrace.install_step_failed(
            step="import_data",
            entry="cli",
            message="数据库不可用 /Users/secret/project/data.duckdb",
            extra={"exit_code": 1},
        )

    name, body = mock_trace.track_setup.call_args.args
    assert name == "install.step_failed"
    assert body["step"] == "import_data"
    assert body["entry"] == "cli"
    assert body["error_class"] == "db_unavailable"
    assert "secret" not in body["message_safe"]
    assert body["exit_code"] == 1


def test_install_complete_swallows_trace_errors() -> None:
    mock_trace = MagicMock()
    mock_trace.track_setup.side_effect = RuntimeError("boom")
    with patch("core.infra.trace.Trace", mock_trace):
        SetupTrace.install_complete(success=True, entry="ui")  # must not raise


def test_install_step_failed_classifies_lock_and_interrupt() -> None:
    mock_trace = MagicMock()
    with patch("core.infra.trace.Trace", mock_trace):
        SetupTrace.install_step_failed(
            step="import_data",
            entry="ui",
            message="Conflicting lock on database",
        )
        SetupTrace.install_step_failed(
            step="resolve_deps",
            entry="cli",
            exc=KeyboardInterrupt(),
        )

    bodies = [call.args[1] for call in mock_trace.track_setup.call_args_list]
    assert bodies[0]["error_class"] == "lock"
    assert bodies[1]["error_class"] == "interrupt"
    assert bodies[1]["exc_type"] == "KeyboardInterrupt"
