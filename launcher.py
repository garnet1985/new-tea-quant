#!/usr/bin/env python3
"""
UI 启动入口。

  python3 launcher.py           生产模式：BFF:8888 托管 fed/build（无需 Node）
  python3 launcher.py -d          开发模式：BFF(8888) + FED dev server(6666)
  python3 launcher.py -dev        同上
"""
from __future__ import annotations

import argparse

from setup.setup import NewTeaQuantSetup
from setup.install_runtime import needs_install, set_ui_dev_mode
from setup.ui_runtime import (
    check_runtime_prerequisites,
    install_ui_runtime,
    launch_ui_stack,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="New Tea Quant UI Launcher")
    parser.add_argument(
        "-d",
        "-dev",
        "--dev",
        action="store_true",
        dest="dev",
        help="开发模式：FED 开发服务器 npm start（端口 6666），BFF 仍为 8888",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    set_ui_dev_mode(args.dev)

    NewTeaQuantSetup.to_root_dir()
    NewTeaQuantSetup.ensure_venv(entry_script=NewTeaQuantSetup.repo_root / "launcher.py")

    if args.dev:
        print("UI 开发模式（-d / -dev）：BFF + FED 开发服务器", flush=True)
    else:
        print("UI 生产模式：BFF 托管静态构建", flush=True)

    ok, msg = check_runtime_prerequisites()
    if not ok:
        print(f"❌ 运行环境检查失败: {msg}", flush=True)
        return 1

    required = needs_install("ui")
    if required:
        print("检测到需要初始化安装，开始安装 UI 依赖...", flush=True)
        try:
            install_ui_runtime(force=True)
        except Exception as e:
            print(f"❌ 安装失败: {e}", flush=True)
            return 1
    else:
        print("安装状态已就绪。", flush=True)

    try:
        launch_ui_stack()
    except Exception as e:
        print(f"❌ UI 启动失败: {e}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
