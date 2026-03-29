#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键安装入口：在仓库根目录执行（需 Python 3.9+）。

根目录无命令行参数；按 INSTALL_STEPS 顺序执行 setup/<step>/install.py。
共用工具见 setup/setup.py。

默认自动创建并使用 venv/；跳过自动 venv：环境变量 NTQ_SKIP_AUTO_VENV=1。
"""
from __future__ import annotations

from setup.setup import NewTeaQuantSetup

# (步骤目录名, 传给该步 install.py 的 argv, enabled=True 则执行该步)
# order is important
INSTALL_STEPS: tuple[tuple[str, tuple[str, ...], bool], ...] = (
    ("sys_req_check", (), True),
    ("resolve_deps", (), True),
    ("init_database", (), True),
    ("setup_data", (), True),
)

def main() -> None:
    NewTeaQuantSetup.to_root_dir()
    NewTeaQuantSetup.ensure_venv()

    NewTeaQuantSetup.print_heading("New Tea Quant 一键安装")

    enabled_steps = [(step, params) for step, params, enabled in INSTALL_STEPS if enabled]
    total_steps = len(enabled_steps)

    for i, (step, params) in enumerate(enabled_steps, start=1):
        NewTeaQuantSetup.print_check_item("running", f"[{i}/{total_steps}] {step}")
        code = NewTeaQuantSetup.run_install_script(step, params)
        if code != 0:
            NewTeaQuantSetup.print_check_item("fail", f"[{i}/{total_steps}] {step} (exit={code})")
            raise SystemExit(code)
        NewTeaQuantSetup.print_check_item("done", f"[{i}/{total_steps}] {step}")

if __name__ == "__main__":
    main()
