#!/usr/bin/env python3
"""
UI 启动入口。

  python3 launcher.py        生产：入口 :8888（BFF 托管 fed/build）
  python3 launcher.py -d     开发：浏览器 :8000（CRA），BFF API 共用 :8888
"""
from __future__ import annotations

from core.infra.cmd_layout import i

import sys

# Windows GBK 编码兼容：强制 UTF-8 输出，保留 emoji 符号
if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import argparse

from core.ui.ports import UI_BFF_PORT, UI_DEV_PORT
from core.infra.setup import Setup


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="New Tea Quant UI Launcher")
    parser.add_argument(
        "-d",
        "-dev",
        "--dev",
        action="store_true",
        dest="dev",
        help=f"开发模式（浏览器 :{UI_DEV_PORT}，共享 BFF :{UI_BFF_PORT}）",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    Setup.runtime.set_ui_dev_mode(args.dev)

    Setup.env.to_root_dir()
    Setup.env.ensure_venv(entry_script=Setup.env.repo_root() / "launcher.py")

    mode = "开发" if args.dev else "生产"
    print(f"UI {mode}模式", flush=True)

    ok, msg = Setup.runtime.check_ui_prerequisites()
    if not ok:
        print(f"{i('error')} {msg}", flush=True)
        return 1

    if Setup.runtime.needs_install("ui"):
        print("正在安装 UI 依赖…", flush=True)
        try:
            Setup.runtime.install_ui(force=True)
        except Exception as e:
            print(f"{i('error')} 安装失败: {e}", flush=True)
            return 1
    else:
        print("依赖已就绪", flush=True)

    try:
        Setup.trace.app_start(entry="ui")
    except Exception:
        pass

    try:
        Setup.runtime.launch_ui()
    except Exception as e:
        print(f"{i('error')} 启动失败: {e}", flush=True)
        print("若页面仍能打开但 /api 报错，请执行: python devcli.py uk", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
