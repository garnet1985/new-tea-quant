"""install_ui_runtime Trace wiring."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from core.infra.setup.core import ui_runtime as ur

pytestmark = pytest.mark.force_run


def test_install_ui_runtime_tracks_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ur, "needs_install", lambda _profile: True)
    monkeypatch.setattr(ur, "_bootstrap_pip", lambda: None)
    monkeypatch.setattr(ur, "_pip_install_bff", lambda: None)
    monkeypatch.setattr(ur, "ui_dev_mode", lambda: True)
    monkeypatch.setattr(ur, "_npm_install_fed", lambda: None)
    monkeypatch.setattr(ur, "sha256_file", lambda _p: "hash")
    monkeypatch.setattr(ur, "mark_runtime", lambda *a, **k: None)
    monkeypatch.setattr(ur.SetupTrace, "ensure_install_id", lambda: None)

    with patch.object(ur.SetupTrace, "install_complete") as complete:
        with patch.object(ur.SetupTrace, "install_step_failed") as failed:
            ur.install_ui_runtime(force=True)

    complete.assert_not_called()
    failed.assert_not_called()


def test_install_ui_runtime_tracks_pip_bff_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ur, "needs_install", lambda _profile: True)
    monkeypatch.setattr(ur, "_bootstrap_pip", lambda: None)

    def _boom() -> None:
        raise RuntimeError("pip failed with /Users/secret/path")

    monkeypatch.setattr(ur, "_pip_install_bff", _boom)
    monkeypatch.setattr(ur, "mark_runtime", lambda *a, **k: None)
    monkeypatch.setattr(ur.SetupTrace, "ensure_install_id", lambda: None)

    with patch.object(ur.SetupTrace, "install_complete") as complete:
        with patch.object(ur.SetupTrace, "install_step_failed") as failed:
            with pytest.raises(RuntimeError):
                ur.install_ui_runtime(force=True)

    failed.assert_called_once()
    assert failed.call_args.kwargs["step"] == "pip_bff"
    assert failed.call_args.kwargs["entry"] == "ui"
    complete.assert_called_once_with(
        success=False,
        entry="ui",
        error_code="pip_bff",
    )


def test_bootstrap_pip_skips_network_when_minimums_met(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = []
    monkeypatch.delenv("NTQ_SKIP_PIP_BOOTSTRAP", raising=False)
    monkeypatch.setattr(ur, "_bootstrap_pip_ready", lambda: True)
    monkeypatch.setattr(ur.subprocess, "run", lambda *a, **k: called.append(True))
    ur._bootstrap_pip()
    assert called == []


def test_bootstrap_pip_ready_accepts_current_toolchain() -> None:
    assert ur._version_meets("26.0.1", (24, 0)) is True
    assert ur._version_meets("64.0", (65,)) is False
    assert ur._version_meets("65.0.0", (65,)) is True
