"""在隔离 venv（仅 BFF requirements）下跑 ``minimal_import_check``。"""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

from core.infra.project_context import ProjectContext

CHECK_MODULE = "core.modules.cli.dev.scripts.minimal_import_check"


def test_ensure_venv_skips_pip_upgrade_and_uses_index_flags(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core.modules.cli.dev.scripts.minimal_import_check import minimal_import_check as mic

    venv_dir = tmp_path / "venv"
    bin_dir = venv_dir / "bin"
    bin_dir.mkdir(parents=True)
    python = bin_dir / "python"
    python.write_text("", encoding="utf-8")
    req = tmp_path / "requirements.txt"
    req.write_text("flask\n", encoding="utf-8")

    monkeypatch.setattr(mic, "BFF_REQUIREMENTS", req)
    monkeypatch.setattr(mic, "_venv_pip_version", lambda _python: "26.0.1")
    monkeypatch.setattr(mic.Utils.pkg, "announce", staticmethod(lambda: None))

    calls: list[tuple] = []

    def _run_pip(argv, **kwargs):
        calls.append((list(argv), kwargs.get("python")))
        return 0

    monkeypatch.setattr(mic.Utils.pkg, "run_pip", staticmethod(_run_pip))
    assert mic._ensure_venv(venv_dir) == python
    assert len(calls) == 1
    argv, py = calls[0]
    assert argv[0] == "install"
    assert "--upgrade" not in argv
    assert "-r" in argv
    assert str(req) in argv
    assert py == str(python)


def test_ui_minimal_import_smoke() -> None:
    if os.environ.get("NTQ_RUN_MINIMAL_IMPORT_CHECK", "").strip().lower() not in (
        "1",
        "true",
        "yes",
    ):
        pytest.skip("CI 单独跑 python -m …minimal_import_check；本地设 NTQ_RUN_MINIMAL_IMPORT_CHECK=1")
    if os.environ.get("NTQ_SKIP_MINIMAL_IMPORT_CHECK", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        pytest.skip("NTQ_SKIP_MINIMAL_IMPORT_CHECK=1")

    proc = subprocess.run(
        [sys.executable, "-m", CHECK_MODULE],
        cwd=str(ProjectContext.path.get_project_root()),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        msg = proc.stdout + "\n" + proc.stderr
        pytest.fail(f"minimal_import_check failed (exit {proc.returncode}):\n{msg}")
