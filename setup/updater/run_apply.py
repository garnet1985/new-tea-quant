#!/usr/bin/env python3
"""
应用升级 CLI 入口。

须从 ``userspace/updater/run_apply.py`` 启动（随 init userspace 解压得到），
勿依赖 ``core/``、``setup/`` 内同名模块，以免升级时被覆盖。

开发时可在仓库根执行::
    python setup/updater/run_apply.py

安装后与 ``<repo>/userspace/updater/run_apply.py`` 为同一套文件。
"""
from __future__ import annotations

import sys
from pathlib import Path

_UPDATER_DIR = Path(__file__).resolve().parent
if str(_UPDATER_DIR) not in sys.path:
    sys.path.insert(0, str(_UPDATER_DIR))

from pipeline import run_upgrade_pipeline  # noqa: E402


def main() -> None:
    """占位：后续解析仓库根、zip 路径、构造 UpgradeContext 并调用 ``run_upgrade_pipeline``。"""
    pass


if __name__ == "__main__":
    main()
