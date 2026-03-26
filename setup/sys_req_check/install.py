#!/usr/bin/env python3
"""
检查当前解释器是否满足 core.system 中的最低 Python 版本。

说明：本文件由 Python 运行；能执行到此处即表示系统已能启动某个 Python，
      无需再检测「是否安装 Python」。若 Windows 上未安装或未加入 PATH，
      用户在双击/运行脚本前就会失败，请使用 run_sys_req_check.bat（会探测
      py / python / python3）或先安装 Python 3.9+。
"""
from __future__ import annotations

import sys
from pathlib import Path

# 必须先加入项目根，否则直接执行本脚本时找不到 core（install.py 同理）
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.system import python_minimum
from core.utils import i


def main() -> None:
    min_ver = python_minimum()
    step_result = 0
    step_icon = i("failed")

    if sys.version_info >= min_ver:
        step_result = 1
        step_icon = i("success")

    print(
        f"Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} - {step_icon}",
        file=sys.stderr,
    )

    if step_result == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
