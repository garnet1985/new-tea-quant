"""Argparse for flat ``devcli`` commands."""

from __future__ import annotations

import argparse

from core.infra.cli.dev import handlers as h
from core.infra.cli.dev.commands import DEFAULT_COMMAND, aliases_for
from core.infra.cli.dev.help_text import DEVCLI_COMMAND_REFERENCE


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="devcli.py",
        description="New Tea Quant 开发命令",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_epilog(),
    )
    parser.add_argument("--verbose", action="store_true", help="详细日志（DEBUG）")

    sub = parser.add_subparsers(dest="command", required=False)

    sub.add_parser("version", help="显示 core 版本").set_defaults(handler=h.cmd_version)

    p_ui = sub.add_parser("ui", help="启动本地 UI（launcher -d）")
    p_ui.add_argument("--kill-first", action="store_true")
    p_ui.add_argument("forward", nargs=argparse.REMAINDER)
    p_ui.set_defaults(handler=h.cmd_ui)

    p_uk = sub.add_parser(
        "ui_kill",
        aliases=aliases_for("ui_kill"),
        help="结束 UI 端口监听",
    )
    p_uk.add_argument("--ntq-only", action="store_true")
    p_uk.add_argument("--port", type=int, action="append")
    p_uk.set_defaults(handler=h.cmd_ui_kill)

    p_ic = sub.add_parser(
        "check_import",
        aliases=aliases_for("check_import"),
        help="UI 最小依赖 import 冒烟",
    )
    p_ic.add_argument("forward", nargs=argparse.REMAINDER)
    p_ic.set_defaults(handler=h.cmd_check_import)

    sub.add_parser(
        "clear_global_cache",
        aliases=aliases_for("clear_global_cache"),
        help="清理 userspace/.ntq",
    ).set_defaults(handler=h.cmd_clear_global_cache)

    sub.add_parser(
        "clear_strategy_cache",
        aliases=aliases_for("clear_strategy_cache"),
        help="清理策略模拟磁盘 + DB 工作台缓存",
    ).set_defaults(handler=h.cmd_clear_strategy_cache)

    sub.add_parser(
        "cache_clear_db",
        aliases=aliases_for("cache_clear_db"),
        help="仅清理 DB 工作台快照",
    ).set_defaults(handler=h.cmd_cache_clear_db)

    sub.add_parser(
        "cache_clear_disk",
        aliases=aliases_for("cache_clear_disk"),
        help="仅删除各策略 results/ 目录",
    ).set_defaults(handler=h.cmd_cache_clear_disk)

    p_dbc = sub.add_parser(
        "db_checkpoint",
        aliases=aliases_for("db_checkpoint"),
        help="DuckDB WAL 合并",
    )
    p_dbc.add_argument(
        "--recover",
        dest="recover_corrupt_wal",
        action="store_true",
        help="WAL 损坏时删除 .wal 后重试",
    )
    p_dbc.set_defaults(handler=h.cmd_db_checkpoint)

    p_ex = sub.add_parser(
        "data_export_init",
        aliases=aliases_for("data_export_init"),
        help="打包演示数据 zip",
    )
    p_ex.add_argument("forward", nargs=argparse.REMAINDER)
    p_ex.set_defaults(handler=h.cmd_data_export_init)

    p_pu = sub.add_parser(
        "userspace_package",
        aliases=aliases_for("userspace_package"),
        help="同步 init userspace + zip",
    )
    p_pu.add_argument("--no-zip", action="store_true")
    p_pu.set_defaults(handler=h.cmd_userspace_package)

    p_pack = sub.add_parser(
        "pack",
        aliases=aliases_for("pack"),
        help="版本发布检查流水线",
    )
    p_pack.add_argument("--version", required=True, help="目标版本 X.Y.Z 或 vX.Y.Z")
    p_pack.add_argument("--check-only", action="store_true")
    p_pack.add_argument("--skip-tests", action="store_true")
    p_pack.add_argument("--skip-ic", action="store_true")
    p_pack.add_argument("--skip-fed-build", action="store_true")
    p_pack.add_argument("--skip-py39", action="store_true")
    p_pack.add_argument(
        "--package-userspace",
        action="store_true",
        help="检查通过后打包 init userspace",
    )
    p_pack.add_argument(
        "--skip-dep-check",
        action="store_true",
        help="跳过依赖安装风险检测（Windows 兼容性、未使用依赖等）",
    )
    p_pack.set_defaults(handler=h.cmd_pack)

    p_cd = sub.add_parser(
        "check_deps",
        aliases=aliases_for("check_deps"),
        help="依赖安装风险检测（Windows 兼容性、未使用依赖等）",
    )
    p_cd.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")
    p_cd.set_defaults(handler=h.cmd_check_deps)

    p_ssp = sub.add_parser(
        "sample_stock_pool",
        aliases=aliases_for("sample_stock_pool"),
        help="分层抽样 N 只股票并激活样本池",
    )
    p_ssp.add_argument("count", type=int)
    p_ssp.set_defaults(handler=h.cmd_sample_stock_pool)

    sub.add_parser(
        "pool_clear",
        aliases=aliases_for("pool_clear"),
        help="取消样本股票池（恢复全量 renew）",
    ).set_defaults(handler=h.cmd_pool_clear)

    return parser


def _epilog() -> str:
    return "\n" + DEVCLI_COMMAND_REFERENCE + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    from core.infra.cli.dev.abbrev import expand_argv

    expanded = expand_argv(argv or [])
    parser = build_parser()
    args = parser.parse_args(expanded)

    if args.command is None:
        args.command = DEFAULT_COMMAND

    if getattr(args, "handler", None) is None and args.command == DEFAULT_COMMAND:
        args.handler = h.cmd_version

    if hasattr(args, "forward"):
        args.forward = h.normalize_forward(args.forward or [])
    return args
