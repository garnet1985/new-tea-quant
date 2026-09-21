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
    monkeypatch.setattr(cr, "_ordered_cli_steps", lambda: ["init_userspace"])
    monkeypatch.setattr(cr.NewTeaQuantSetup, "to_root_dir", lambda: None)
    monkeypatch.setattr(cr.NewTeaQuantSetup, "print_check_item", lambda *a, **k: None)
    monkeypatch.setattr(cr.NewTeaQuantSetup, "print_check_ok", lambda *a, **k: None)
    monkeypatch.setattr(cr, "mark_runtime", lambda *a, **k: None)
    monkeypatch.setattr(cr.SetupTrace, "install_complete", lambda **k: None)
    monkeypatch.setattr(cr.SetupTrace, "install_step_failed", lambda **k: None)
    monkeypatch.setattr(cr.SetupTrace, "ensure_install_id", lambda: None)
    monkeypatch.setattr(cr, "_run_step", lambda *a, **k: 0)
    monkeypatch.setattr(cr.setup_session, "record_step", lambda *a, **k: None)
    monkeypatch.setattr(cr.setup_session, "mark_pipeline_complete", lambda **k: None)
    monkeypatch.setattr(cr.setup_session, "mark_pipeline_failed", lambda *a, **k: None)
    monkeypatch.setattr(cr, "mark_cli_success_fingerprint", lambda: None)

    def _ask(*, source=""):
        asked.append(source)
        return False

    monkeypatch.setattr("core.infra.trace.Trace.ask_permission", staticmethod(_ask))
    cr.install_cli_runtime(force=True)
    assert asked == []


def test_ensure_cli_install_passes_if_needed(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.infra.setup.core import cli_runtime as cr

    recorded: dict = {}

    def _run(cmd, cwd=None, env=None):
        recorded["cmd"] = list(cmd)
        return type("Proc", (), {"returncode": 0})()

    monkeypatch.setattr(cr.subprocess, "run", _run)
    assert cr.ensure_cli_install_via_install_py() == 0
    assert recorded["cmd"][-2:] == [str(cr.REPO_ROOT / "install.py"), "--if-needed"]


def test_install_py_default_runs_even_when_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "ntq_install_entry", ir.REPO_ROOT / "install.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    monkeypatch.setattr(mod.Setup.env, "to_root_dir", lambda: None)
    monkeypatch.setattr(mod.Setup.env, "ensure_venv", lambda **_k: None)
    monkeypatch.setattr(mod.Setup.runtime, "needs_install", lambda _profile: False)
    called: list = []
    monkeypatch.setattr(
        mod.Setup.runtime, "install_cli", lambda **kwargs: called.append(kwargs)
    )
    assert mod.main([]) == 0
    assert called == [{"force": True}]
    called.clear()
    assert mod.main(["--if-needed"]) == 0
    assert called == []
    called.clear()
    assert (
        mod.main(
            [
                "--userspace",
                "/tmp/ntq-userspace",
                "--userspace-conflict",
                "overwrite",
                "--db",
                "postgresql",
                "--db-host",
                "127.0.0.1",
                "--db-port",
                "5432",
                "--db-name",
                "ntq",
                "--db-user",
                "postgres",
                "--db-password",
                "secret",
                "--db-schema",
                "public",
            ]
        )
        == 0
    )
    assert called == [
        {
            "force": True,
            "userspace": "/tmp/ntq-userspace",
            "userspace_conflict": "overwrite",
            "db": "postgresql",
            "db_host": "127.0.0.1",
            "db_port": "5432",
            "db_name": "ntq",
            "db_user": "postgres",
            "db_password": "secret",
            "db_schema": "public",
        }
    ]


def test_run_step_passes_userspace_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.infra.setup.core import cli_runtime as cr
    from core.infra.setup.core.cli_install_options import CliInstallOptions

    recorded: dict = {}

    def _run(step_name, script_args=(), extra_env=None):
        recorded["step"] = step_name
        recorded["env"] = dict(extra_env or {})
        return 0

    monkeypatch.setattr(cr.NewTeaQuantSetup, "run_install_script", _run)
    options = CliInstallOptions(
        userspace="/tmp/ntq-custom-userspace",
        userspace_conflict="overwrite",
    )
    assert cr._run_step("init_userspace", options) == 0
    assert recorded["step"] == "init_userspace"
    assert recorded["env"]["NTQ_USERSPACE_CONFLICT_POLICY"] == "overwrite"
    assert recorded["env"]["NTQ_USERSPACE_TARGET_PATH"].endswith("ntq-custom-userspace")


def test_cli_install_writes_shared_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core.infra.setup.core import cli_runtime as cr
    from core.infra.setup.core import setup_session

    monkeypatch.setattr(setup_session, "STATE_FILE", tmp_path / "setup-runtime.json")
    monkeypatch.setattr(cr, "needs_install", lambda _profile: True)
    monkeypatch.setattr(cr, "_ordered_cli_steps", lambda: ["init_userspace", "db_connection"])
    monkeypatch.setattr(cr.NewTeaQuantSetup, "to_root_dir", lambda: None)
    monkeypatch.setattr(cr.NewTeaQuantSetup, "print_check_item", lambda *a, **k: None)
    monkeypatch.setattr(cr.NewTeaQuantSetup, "print_check_ok", lambda *a, **k: None)
    monkeypatch.setattr(cr, "mark_runtime", lambda *a, **k: None)
    monkeypatch.setattr(cr, "mark_cli_success_fingerprint", lambda: None)
    monkeypatch.setattr(cr.SetupTrace, "install_complete", lambda **k: None)
    monkeypatch.setattr(cr.SetupTrace, "install_step_failed", lambda **k: None)
    monkeypatch.setattr(cr.SetupTrace, "ensure_install_id", lambda: None)
    monkeypatch.setattr(cr, "_run_step", lambda *a, **k: 0)
    monkeypatch.setattr(cr, "_apply_db_config", lambda *_a, **_k: None)

    cr.install_cli_runtime(force=True)
    state = json.loads((tmp_path / "setup-runtime.json").read_text(encoding="utf-8"))
    assert state["isReady"] is True
    assert state["installSource"] == "cli"
    by_id = {item["stepId"]: item["status"] for item in state["stepStates"]}
    assert by_id["init_userspace"] == "success"
    assert by_id["db_connection"] == "success"
    assert by_id["resolve_ml_deps"] == "success"
