"""Repo-root helpers shared by ``cli.dev.scripts``."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _detect_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "core" / "system.json").is_file():
            return parent
        if (parent / "requirements.in").is_file() and (parent / "core").is_dir():
            return parent
    # services → dev → cli → infra → core → repo
    return here.parents[5]


REPO_ROOT = _detect_repo_root()


def repo_python() -> Path:
    """发布/开发检查优先使用仓库 ``venv`` 解释器（含 Flask 等 dev 依赖）。"""
    if os.name == "nt":
        vpy = REPO_ROOT / "venv" / "Scripts" / "python.exe"
    else:
        vpy = REPO_ROOT / "venv" / "bin" / "python"
    if vpy.is_file():
        return vpy
    return Path(sys.executable)
