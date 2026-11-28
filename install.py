#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI 应用安装入口（与 ``launcher.py`` 对称）：

  python install.py                 执行 CLI 安装，并默认从官网下载、导入演示数据
  python install.py --skip-demo-data
                                    同上，但跳过演示数据下载/导入
  python install.py --if-needed     仅未就绪时安装（``cli.py`` 自动触发）。
                                    依赖变化只更新依赖；完整安装时默认仍导入演示数据。

安装步骤开始前须同意使用条款：交互终端只认 y / Y，其他输入停止。
无终端时用 ``--accept-license`` 或 ``NTQ_ACCEPT_LICENSE=1``。
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


def _wire_official_package_fetcher() -> None:
    """入口组装：官网下载接到 Setup（setup 包内不 import ntq_external）。"""
    try:
        from core.modules.ntq_external.setup_bridge import wire_setup_package_fetcher

        wire_setup_package_fetcher()
    except ImportError:
        pass


_HELP_EPILOG = """
默认行为
  · 同意使用条款后跑完整 CLI 安装（系统检查 → 依赖 → userspace → 数据库 → 演示数据）
  · 数据库默认 DuckDB；userspace 默认 <仓库根>/userspace（已存在则 skip 保留）
  · 演示数据默认从官网公开接口下载 data_demo.zip 并导入（约 22MB；会覆盖同名表）
  · 下载过程在终端显示进度（有 Content-Length 时为百分比）

常用示例
  python install.py
  python install.py --skip-demo-data
  python install.py --accept-license
  python install.py --db postgresql --db-host 127.0.0.1 --db-name ntq --db-user ntq --db-password secret
  python install.py --if-needed

跳过演示数据后若要补导：python cli.py id
""".strip()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="install.py",
        description="New Tea Quant CLI 安装（须先同意使用条款；可用参数指定 userspace / 数据库）",
        epilog=_HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--accept-license",
        action="store_true",
        help="非交互环境明示同意当前使用条款（默认：交互终端输入 y；也可用 NTQ_ACCEPT_LICENSE=1）",
    )
    parser.add_argument(
        "--if-needed",
        action="store_true",
        help="仅在 CLI 未就绪时安装（cli.py 自动触发）。依赖变更只更新依赖；完整安装默认仍导入演示数据",
    )
    parser.add_argument(
        "--skip-demo-data",
        action="store_true",
        help="跳过演示数据下载与导入（默认会从官网拉取并导入；跳过后可用 python cli.py id 补导）",
    )
    parser.add_argument(
        "--userspace",
        default=None,
        metavar="PATH",
        help="userspace 路径（默认：<仓库根>/userspace）",
    )
    parser.add_argument(
        "--userspace-conflict",
        choices=("skip", "overwrite"),
        default=None,
        help="目标路径已存在时：skip 保留 / overwrite 覆盖（默认：skip）",
    )
    parser.add_argument(
        "--db",
        choices=("duckdb", "postgresql", "mysql"),
        default=None,
        help="数据库类型（默认：duckdb）",
    )
    parser.add_argument("--db-host", default=None, metavar="HOST", help="PostgreSQL / MySQL host")
    parser.add_argument("--db-port", default=None, metavar="PORT", help="PostgreSQL / MySQL port")
    parser.add_argument(
        "--db-name",
        default=None,
        metavar="NAME",
        help="PostgreSQL / MySQL 数据库名",
    )
    parser.add_argument("--db-user", default=None, metavar="USER", help="PostgreSQL / MySQL 用户")
    parser.add_argument(
        "--db-password",
        default=None,
        metavar="PASS",
        help="PostgreSQL / MySQL 密码",
    )
    parser.add_argument(
        "--db-schema",
        default=None,
        metavar="SCHEMA",
        help="PostgreSQL schema（默认：public）",
    )
    return parser.parse_args(argv)


def _install_kwargs(args: argparse.Namespace) -> dict:
    kwargs: dict = {
        "force": True,
        "import_demo": not bool(args.skip_demo_data),
    }
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


def _install(
    args: argparse.Namespace,
    *,
    force: bool,
    deps_only: bool = False,
) -> int:
    kwargs = _install_kwargs(args)
    kwargs["force"] = force
    if deps_only:
        kwargs["deps_only"] = True
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


def _ensure_license(args: argparse.Namespace) -> bool:
    return Setup.license.ensure_accepted(
        source="install",
        assume_accepted=bool(args.accept_license),
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    Setup.env.to_root_dir()
    Setup.env.ensure_venv(entry_script=Setup.env.repo_root() / "install.py")
    _wire_official_package_fetcher()

    if args.if_needed:
        if not Setup.runtime.needs_install("cli"):
            if args.accept_license:
                Setup.license.ensure_accepted(source="install", assume_accepted=True)
            print("CLI 安装状态已就绪。", flush=True)
            return 0
        if not _ensure_license(args):
            return 1
        scope = Setup.runtime.cli_install_scope()
        if scope == "deps_only":
            print("检测到 requirements.txt 变更，正在更新 Python 依赖…", flush=True)
            return _install(args, force=False, deps_only=True)
        print("检测到需要初始化安装，开始 CLI 安装...", flush=True)
        return _install(args, force=False)

    if not _ensure_license(args):
        return 1
    demo_note = "跳过演示数据" if args.skip_demo_data else "含演示数据（官网下载）"
    print(f"开始 CLI 安装…（{demo_note}）", flush=True)
    return _install(args, force=True)


if __name__ == "__main__":
    raise SystemExit(main())
