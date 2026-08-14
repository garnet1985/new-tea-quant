#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI 应用安装入口（与 ``launcher.py`` 对称）：

  python install.py    检测并按需执行 CLI 安装（setup 步骤）

``launcher.py`` 负责 UI 安装与启动；本脚本仅负责 CLI，不启动 UI。
"""
from __future__ import annotations

import sys

# Windows GBK 编码兼容：强制 UTF-8 输出，保留 emoji 符号
if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from core.infra.setup import Setup


def main() -> int:
    Setup.env.to_root_dir()
    Setup.env.ensure_venv(entry_script=Setup.env.repo_root() / "install.py")

    if Setup.runtime.needs_install("cli"):
        scope = Setup.runtime.cli_install_scope()
        if scope == "deps_only":
            print("检测到 requirements.txt 变更，正在更新 Python 依赖…", flush=True)
        else:
            print("检测到需要初始化安装，开始 CLI 安装...", flush=True)
        try:
            Setup.runtime.install_cli()
        except Exception as e:
            try:
                from core.infra.cmd_layout import i

                mark = i("error")
            except Exception:
                mark = "[FAIL]"
            print(f"{mark} CLI 安装失败: {e}", flush=True)
            return 1
    else:
        print("CLI 安装状态已就绪。", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
