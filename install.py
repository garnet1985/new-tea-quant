#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI 初始化安装入口（最小依赖）：
- 检查运行环境
- 安装 BFF/FED 启动依赖
- 启动 UI（BFF + FED）
"""
from __future__ import annotations

from setup.setup import NewTeaQuantSetup
from setup.ui_runtime import check_runtime_prerequisites, install_ui_runtime, launch_ui_stack


def main() -> int:
    NewTeaQuantSetup.to_root_dir()
    NewTeaQuantSetup.ensure_venv()

    ok, msg = check_runtime_prerequisites()
    if not ok:
        print(f"❌ 环境检查失败: {msg}", flush=True)
        return 1

    try:
        install_ui_runtime(force=True)
    except Exception as e:
        print(f"❌ 初始化安装失败: {e}", flush=True)
        return 1

    try:
        launch_ui_stack()
    except Exception as e:
        print(f"❌ UI 启动失败: {e}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
