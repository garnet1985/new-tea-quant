#!/usr/bin/env python3
"""安装可选机器学习依赖（requirements-ml.txt：xgboost、shap）。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = next(
    p
    for p in Path(__file__).resolve().parents
    if (p / "install.py").is_file() and (p / "core" / "system.json").is_file()
)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.infra.setup.core.env import NewTeaQuantSetup
from core.infra.setup.core.pip_index import announce_pip_index, pip_net_flags

NewTeaQuantSetup.ensure_venv_for_setup_step(__file__)


def main() -> int:
    print(f"当前机器学习依赖安装解释器: {sys.executable}", file=sys.stderr)
    announce_pip_index()

    req = _REPO_ROOT / "requirements-ml.txt"
    if not req.is_file():
        print(f"错误: 未找到 requirements-ml.txt: {req}", file=sys.stderr)
        return 1

    cmd: list[str] = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--no-compile",
        *pip_net_flags(),
        "-r",
        str(req),
    ]
    return int(subprocess.run(cmd, cwd=str(_REPO_ROOT)).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
