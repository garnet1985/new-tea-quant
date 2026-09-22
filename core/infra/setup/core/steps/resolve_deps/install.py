#!/usr/bin/env python3
"""
安装 Python 依赖（requirements.txt）。
"""
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
from core.infra.utils import Utils

NewTeaQuantSetup.ensure_venv_for_setup_step(__file__)


def main() -> int:
    print(f"当前依赖安装解释器: {sys.executable}", file=sys.stderr)
    Utils.pkg.announce()

    if Utils.pkg.pip_meets_minimum((24, 0)):
        print("pip 已满足最低版本，跳过联网自升级。", file=sys.stderr)
    else:
        print("升级 pip …", file=sys.stderr)
        upgraded = Utils.pkg.run_pip(["install", "--upgrade", "pip"])
        if upgraded != 0 and not Utils.pkg.pip_meets_minimum((21, 0)):
            print(Utils.pkg.pip_hint(), file=sys.stderr)

    print("清除 pip cache …", file=sys.stderr)
    subprocess.run([sys.executable, "-m", "pip", "cache", "purge"], check=False)

    req = _REPO_ROOT / "requirements.txt"
    if not req.is_file():
        print(f"错误: 未找到 requirements.txt: {req}", file=sys.stderr)
        return 1

    return Utils.pkg.run_pip(
        [
            "install",
            "--no-compile",
            "--only-binary",
            "numpy,pandas,duckdb,psycopg2-binary,cffi,curl-cffi,lxml,mini-racer,psutil",
            "-r",
            str(req),
        ],
        cwd=str(_REPO_ROOT),
    )


if __name__ == "__main__":
    raise SystemExit(main())
