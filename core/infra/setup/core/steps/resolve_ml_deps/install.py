#!/usr/bin/env python3
"""安装可选机器学习依赖（requirements-ml.txt：xgboost、shap）。"""
from __future__ import annotations

import os
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

NewTeaQuantSetup.ensure_venv_for_setup_step(__file__)


def _use_china_mirror() -> bool:
    raw = os.environ.get("USE_CHINA_MIRROR", "").strip().lower()
    return raw in ("1", "true", "yes")


def main() -> int:
    print(f"当前机器学习依赖安装解释器: {sys.executable}", file=sys.stderr)

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
        "-r",
        str(req),
    ]
    if _use_china_mirror():
        print("使用清华 PyPI 镜像（USE_CHINA_MIRROR=1）", file=sys.stderr)
        cmd.extend(
            [
                "-i",
                "https://pypi.tuna.tsinghua.edu.cn/simple",
                "--trusted-host",
                "pypi.tuna.tsinghua.edu.cn",
            ]
        )

    r = subprocess.run(cmd, cwd=str(_REPO_ROOT))
    return int(r.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
