from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.infra.setup.core import install_runtime as ir


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


@pytest.mark.force_run
def test_install_does_not_ask_trace_permission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.infra.setup.core import cli_runtime as cr

    asked = []

    monkeypatch.setattr(cr, "needs_install", lambda _profile: True)
    monkeypatch.setattr(cr, "cli_install_scope", lambda: "full")
    monkeypatch.setattr(cr, "_ordered_cli_steps", lambda: ["init_userspace"])
    monkeypatch.setattr(cr.NewTeaQuantSetup, "to_root_dir", lambda: None)
    monkeypatch.setattr(cr.NewTeaQuantSetup, "print_check_item", lambda *a, **k: None)
    monkeypatch.setattr(cr, "mark_runtime", lambda *a, **k: None)
    monkeypatch.setattr(cr, "sha256_file", lambda _p: "hash")
    monkeypatch.setattr(cr.SetupTrace, "install_complete", lambda **k: None)
    monkeypatch.setattr(cr, "_run_step", lambda _step_id: 0)

    def _ask(*, source=""):
        asked.append(source)
        return False

    monkeypatch.setattr("core.infra.trace.Trace.ask_permission", staticmethod(_ask))
    cr.install_cli_runtime(force=True)
    assert asked == []
