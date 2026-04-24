#!/usr/bin/env python3
"""
安装 Python 依赖（requirements.txt）。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from setup.setup import NewTeaQuantSetup

NewTeaQuantSetup.ensure_venv_for_setup_step(__file__)


def _use_china_mirror() -> bool:
    raw = os.environ.get("USE_CHINA_MIRROR", "").strip().lower()
    return raw in ("1", "true", "yes")


def main() -> int:
    print(f"当前依赖安装解释器: {sys.executable}", file=sys.stderr)
    req = _REPO_ROOT / "requirements.txt"
    if not req.is_file():
        print(f"错误: 未找到 requirements.txt: {req}", file=sys.stderr)
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
