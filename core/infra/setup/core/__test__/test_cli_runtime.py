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
def test_ask_permission_runs_after_install_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.infra.setup.core import cli_runtime as cr

    order: list[str] = []

    monkeypatch.setattr(cr, "needs_install", lambda _profile: True)
    monkeypatch.setattr(cr, "cli_install_scope", lambda: "full")
    monkeypatch.setattr(cr, "_ordered_cli_steps", lambda: ["init_userspace"])
    monkeypatch.setattr(cr.NewTeaQuantSetup, "to_root_dir", lambda: None)
    monkeypatch.setattr(cr.NewTeaQuantSetup, "print_check_item", lambda *a, **k: None)
    monkeypatch.setattr(cr, "mark_runtime", lambda *a, **k: None)
    monkeypatch.setattr(cr, "sha256_file", lambda _p: "hash")
    monkeypatch.setattr(cr.SetupTrace, "install_complete", lambda **k: None)

    def _run_step(step_id: str) -> int:
        order.append(f"step:{step_id}")
        return 0

    monkeypatch.setattr(cr, "_run_step", _run_step)
    monkeypatch.setattr(
        cr,
        "_ask_trace_permission_after_install",
        lambda: order.append("ask"),
    )

    cr.install_cli_runtime(force=True)
    assert order == ["step:init_userspace", "ask"]


@pytest.mark.force_run
def test_ask_permission_skipped_when_install_step_fails(
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
    monkeypatch.setattr(cr.SetupTrace, "install_complete", lambda **k: None)
    monkeypatch.setattr(cr, "_run_step", lambda _step_id: 1)
    monkeypatch.setattr(
        cr,
        "_ask_trace_permission_after_install",
        lambda: asked.append(True),
    )

    with pytest.raises(RuntimeError, match="init_userspace"):
        cr.install_cli_runtime(force=True)
    assert asked == []
