#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI 应用安装入口（与 ``launcher.py`` 对称）：

  python install.py              执行 CLI 安装（已装过也会再跑一遍步骤）
  python install.py --if-needed  仅未就绪时安装（``cli.py`` 自动触发）

``launcher.py`` 负责 UI 安装与启动；本脚本仅负责 CLI，不启动 UI。
"""
from __future__ import annotations

import argparse
import sys

# Windows GBK 编码兼容：强制 UTF-8 输出，保留 emoji 符号
if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from core.infra.setup import Setup


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="New Tea Quant CLI 安装")
    parser.add_argument(
        "--if-needed",
        action="store_true",
        help="仅在 CLI 未就绪时安装（cli.py 自动触发）",
    )
    return parser.parse_args(argv)


def _install(*, force: bool) -> int:
    try:
        Setup.runtime.install_cli(force=force)
    except Exception as e:
        try:
            from core.infra.cmd_layout import i

            mark = i("error")
        except Exception:
            mark = "[FAIL]"
        print(f"{mark} CLI 安装失败: {e}", flush=True)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    Setup.env.to_root_dir()
    Setup.env.ensure_venv(entry_script=Setup.env.repo_root() / "install.py")

    if args.if_needed:
        if not Setup.runtime.needs_install("cli"):
            print("CLI 安装状态已就绪。", flush=True)
            return 0
        scope = Setup.runtime.cli_install_scope()
        if scope == "deps_only":
            print("检测到 requirements.txt 变更，正在更新 Python 依赖…", flush=True)
        else:
            print("检测到需要初始化安装，开始 CLI 安装...", flush=True)
        return _install(force=False)

    print("开始 CLI 安装…", flush=True)
    return _install(force=True)


if __name__ == "__main__":
    raise SystemExit(main())
