"""在隔离 venv（仅 BFF requirements）下跑 ``minimal_import_check``。"""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

from core.infra.project_context import ProjectContext

CHECK_MODULE = "core.infra.cli.dev.scripts.minimal_import_check"


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
