#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键安装入口：在仓库根目录执行（需 Python 3.9+）。

根目录无命令行参数；按下方 _INSTALL_STEPS 顺序执行；各子步骤的选项见
setup/<step>/install.py。共用工具见 setup/setup.py。

默认自动创建并使用 venv/；跳过自动 venv：环境变量 NTQ_SKIP_AUTO_VENV=1。

可选 Demo：INSTALL_DEMO_DATA=1（仍由 demo 子步骤自行判断是否交互等）。
"""
from __future__ import annotations

import subprocess
import sys

from setup.setup import NewTeaQuantSetup

# (步骤目录名, 传给该步 install.py 的 argv, disabled=True 则始终跳过该步)
# order is important
INSTALL_STEPS: tuple[tuple[str, tuple[str, ...], bool], ...] = (
    ("sys_req_check", "", True),
    ("resolve_deps", "", True),
    ("init_database", "", True),
    ("import_demo_data", "", False),
)

def main() -> None:
    NewTeaQuantSetup.to_root_dir()
    NewTeaQuantSetup.ensure_venv()

    NewTeaQuantSetup.print_heading("New Tea Quant 一键安装")

    total_steps = 0
    for step, params, is_enabled in INSTALL_STEPS:
        if is_enabled:
            total_steps += 1

    for i, (step, params, is_enabled) in enumerate(INSTALL_STEPS, start=1):
        if is_enabled:
            NewTeaQuantSetup.print_info(f"开始步骤 {i}/{total_steps}", f"{step}", "ongoing")

            subprocess.run([sys.executable, str(NewTeaQuantSetup.repo_root / "setup" / step / "install.py"), params], cwd=str(NewTeaQuantSetup.repo_root))
            
            NewTeaQuantSetup.print_info(f"步骤 {i}", "已经完成", "green_dot")


if __name__ == "__main__":
    main()
