#!/usr/bin/env python3
"""
UI 启动入口。

  python3 launcher.py        生产：BFF 托管 fed/build
  python3 launcher.py -d     开发：FED dev server + BFF API
"""
from __future__ import annotations

import argparse

from core.ui.ports import BFF_DEFAULT_PORT, FED_DEV_PORT
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
        help=f"开发模式（FED :{FED_DEV_PORT}，BFF :{BFF_DEFAULT_PORT}）",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    set_ui_dev_mode(args.dev)

    NewTeaQuantSetup.to_root_dir()
    NewTeaQuantSetup.ensure_venv(entry_script=NewTeaQuantSetup.repo_root / "launcher.py")

    mode = "开发" if args.dev else "生产"
    print(f"UI {mode}模式", flush=True)

    ok, msg = check_runtime_prerequisites()
    if not ok:
        print(f"❌ {msg}", flush=True)
        return 1

    if needs_install("ui"):
        print("正在安装 UI 依赖…", flush=True)
        try:
            install_ui_runtime(force=True)
        except Exception as e:
            print(f"❌ 安装失败: {e}", flush=True)
            return 1
    else:
        print("依赖已就绪", flush=True)

    try:
        launch_ui_stack()
    except Exception as e:
        print(f"❌ 启动失败: {e}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
