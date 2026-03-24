#!/usr/bin/env python3
"""
安装流程中的一步：可选导入 Demo 数据。

由仓库根目录 install.py 按顺序调用；是否进入本步由环境变量 INSTALL_DEMO_DATA=1
（安装前在 shell 中设置）及根目录 install 的步骤表共同决定。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def main() -> int:
    if os.environ.get("INSTALL_DEMO_DATA", "0").strip() != "1":
        return 0
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print(
            "非交互终端，跳过 Demo 导入。可手动执行: "
            f"{sys.executable} -m setup.demo_data_handler",
            file=sys.stderr,
        )
        return 0
    r = subprocess.run(
        [sys.executable, "-m", "setup.demo_data_handler"],
        cwd=str(_REPO_ROOT),
    )
    return int(r.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
