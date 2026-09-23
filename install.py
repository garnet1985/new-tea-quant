#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI 应用安装入口（与 ``launcher.py`` 对称）：

  python install.py              执行 CLI 安装（已装过也会再跑一遍步骤）
  python install.py --if-needed  仅未就绪时安装（``cli.py`` 自动触发）

不询问 userspace / 数据库：省略参数走默认（<repo>/userspace + DuckDB）；
带了参数就必须按参数执行，失败则停止并报错。

``launcher.py`` 负责 UI 安装与启动；本脚本仅负责 CLI，不启动 UI。
安装进度写入 ``.ntq/setup-runtime.json``，与 UI 向导同一份状态。
"""
from __future__ import annotations

import argparse
import sys

# Windows GBK 编码兼容：强制 UTF-8 输出，保留 emoji 符号
if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from core.infra.setup import Setup


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="New Tea Quant CLI 安装（不询问；可用参数指定 userspace / 数据库）"
    )
    parser.add_argument(
        "--if-needed",
        action="store_true",
        help="仅在 CLI 未就绪时安装（cli.py 自动触发）",
    )
    parser.add_argument(
        "--userspace",
        default=None,
        help="userspace 路径（默认 <仓库根>/userspace）",
    )
    parser.add_argument(
        "--userspace-conflict",
        choices=("skip", "overwrite"),
        default=None,
        help="目标路径已存在时：skip 保留当前目录 / overwrite 覆盖（默认 skip）",
    )
    parser.add_argument(
        "--db",
        choices=("duckdb", "postgresql", "mysql"),
        default=None,
        help="数据库类型（默认 duckdb）",
    )
    parser.add_argument("--db-host", default=None, help="PostgreSQL / MySQL host")
    parser.add_argument("--db-port", default=None, help="PostgreSQL / MySQL port")
    parser.add_argument("--db-name", default=None, help="PostgreSQL / MySQL 数据库名")
    parser.add_argument("--db-user", default=None, help="PostgreSQL / MySQL 用户")
    parser.add_argument("--db-password", default=None, help="PostgreSQL / MySQL 密码")
    parser.add_argument(
        "--db-schema",
        default=None,
        help="PostgreSQL schema（默认 public）",
    )
    return parser.parse_args(argv)


def _install_kwargs(args: argparse.Namespace) -> dict:
    kwargs: dict = {"force": True}
    if args.userspace is not None:
        kwargs["userspace"] = args.userspace
    if args.userspace_conflict is not None:
        kwargs["userspace_conflict"] = args.userspace_conflict
    if args.db is not None:
        kwargs["db"] = args.db
    if args.db_host is not None:
        kwargs["db_host"] = args.db_host
    if args.db_port is not None:
        kwargs["db_port"] = args.db_port
    if args.db_name is not None:
        kwargs["db_name"] = args.db_name
    if args.db_user is not None:
        kwargs["db_user"] = args.db_user
    if args.db_password is not None:
        kwargs["db_password"] = args.db_password
    if args.db_schema is not None:
        kwargs["db_schema"] = args.db_schema
    return kwargs


def _install(args: argparse.Namespace, *, force: bool) -> int:
    kwargs = _install_kwargs(args)
    kwargs["force"] = force
    try:
        Setup.runtime.install_cli(**kwargs)
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
        return _install(args, force=False)

    print("开始 CLI 安装…", flush=True)
    return _install(args, force=True)


if __name__ == "__main__":
    raise SystemExit(main())
