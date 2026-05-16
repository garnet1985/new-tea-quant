#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI 应用安装入口（与 ``launcher.py`` 对称）：

  python install.py    检测并按需执行 CLI 安装（setup 步骤）

``launcher.py`` 负责 UI 安装与启动；本脚本仅负责 CLI，不启动 UI。
"""
from __future__ import annotations

from setup.cli_runtime import install_cli_runtime
from setup.install_runtime import needs_install
from setup.setup import NewTeaQuantSetup


def main() -> int:
    NewTeaQuantSetup.to_root_dir()
    NewTeaQuantSetup.ensure_venv(entry_script=NewTeaQuantSetup.repo_root / "install.py")

    if needs_install("cli"):
        print("检测到需要初始化安装，开始 CLI 安装...", flush=True)
        try:
            install_cli_runtime(force=True)
        except Exception as e:
            print(f"❌ CLI 安装失败: {e}", flush=True)
            return 1
    else:
        print("CLI 安装状态已就绪。", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
