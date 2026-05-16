from __future__ import annotations

import json
from pathlib import Path

import pytest

from setup import install_runtime as ir


def test_needs_install_cli_when_runtime_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_dir = tmp_path / ".ntq"
    state_dir.mkdir()
    req = tmp_path / "requirements.txt"
    req.write_text("pandas\n", encoding="utf-8")
    monkeypatch.setattr(ir, "STATE_FILE", state_dir / "install-state.json")
    monkeypatch.setattr(ir, "REQUIREMENTS", req)
    monkeypatch.setattr(ir, "userspace_ready", lambda: True)
    assert ir.needs_install("cli") is True


def test_needs_install_cli_false_when_marked_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_dir = tmp_path / ".ntq"
    state_dir.mkdir()
    req = tmp_path / "requirements.txt"
    req.write_text("pandas\n", encoding="utf-8")
    state_file = state_dir / "install-state.json"
    state_file.write_text(
        json.dumps(
            {
                "coreVersion": ir.system_meta.version,
                "cli": {"requirementsHash": ir.sha256_file(req)},
                "cliRuntime": {"lastStatus": "success", "lastFailedStepId": ""},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(ir, "STATE_FILE", state_file)
    monkeypatch.setattr(ir, "REQUIREMENTS", req)
    monkeypatch.setattr(ir, "userspace_ready", lambda: True)
    assert ir.needs_install("cli") is False
