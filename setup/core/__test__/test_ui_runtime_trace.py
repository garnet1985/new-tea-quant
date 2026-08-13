"""install_ui_runtime Trace wiring."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from setup.core import ui_runtime as ur

pytestmark = pytest.mark.force_run


def test_install_ui_runtime_tracks_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ur, "needs_install", lambda _profile: True)
    monkeypatch.setattr(ur, "_bootstrap_pip", lambda: None)
    monkeypatch.setattr(ur, "_pip_install_bff", lambda: None)
    monkeypatch.setattr(ur, "ui_dev_mode", lambda: True)
    monkeypatch.setattr(ur, "_npm_install_fed", lambda: None)
    monkeypatch.setattr(ur, "sha256_file", lambda _p: "hash")
    monkeypatch.setattr(ur, "mark_runtime", lambda *a, **k: None)

    with patch.object(ur.SetupTrace, "install_complete") as track:
        ur.install_ui_runtime(force=True)

    track.assert_called_once_with(success=True, entry="ui")


def test_install_ui_runtime_tracks_pip_bff_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ur, "needs_install", lambda _profile: True)
    monkeypatch.setattr(ur, "_bootstrap_pip", lambda: None)

    def _boom() -> None:
        raise RuntimeError("pip failed with /Users/secret/path")

    monkeypatch.setattr(ur, "_pip_install_bff", _boom)
    monkeypatch.setattr(ur, "mark_runtime", lambda *a, **k: None)

    with patch.object(ur.SetupTrace, "install_complete") as track:
        with pytest.raises(RuntimeError):
            ur.install_ui_runtime(force=True)

    track.assert_called_once_with(
        success=False,
        entry="ui",
        error_code="pip_bff",
    )
