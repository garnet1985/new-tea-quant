"""在隔离 venv（仅 BFF requirements）下跑 ``minimal_import_check``。"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CHECK_MODULE = "devtools.quick_tools.minimal_import_check"


def test_ui_minimal_import_smoke() -> None:
    if os.environ.get("NTQ_SKIP_MINIMAL_IMPORT_CHECK", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        pytest.skip("NTQ_SKIP_MINIMAL_IMPORT_CHECK=1")

    proc = subprocess.run(
        [sys.executable, "-m", CHECK_MODULE],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        msg = proc.stdout + "\n" + proc.stderr
        pytest.fail(f"minimal_import_check failed (exit {proc.returncode}):\n{msg}")
