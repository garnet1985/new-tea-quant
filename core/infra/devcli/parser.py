"""Argparse for ``devcli.py``."""

from __future__ import annotations

import argparse

from core.infra.devcli import handlers as h


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="devcli.py",
        description="New Tea Quant 开发命令",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_epilog(),
    )

    sub = parser.add_subparsers(dest="domain", required=True)

    ui = sub.add_parser("ui", help="本地 UI")
    ui_sub = ui.add_subparsers(dest="action", required=True)
    p_run = ui_sub.add_parser("run", help="启动 launcher（:8000）")
    p_run.add_argument("--kill-first", action="store_true")
    p_run.add_argument("forward", nargs=argparse.REMAINDER)
    p_run.set_defaults(handler=h.cmd_ui_run)

    p_kill = ui_sub.add_parser("kill", help="结束 UI 端口监听")
    p_kill.add_argument("--ntq-only", action="store_true")
    p_kill.add_argument("--port", type=int, action="append")
    p_kill.set_defaults(handler=h.cmd_ui_kill)

    check = sub.add_parser("check", help="检查")
    check_sub = check.add_subparsers(dest="action", required=True)
    p_ic = check_sub.add_parser("import", help="UI 最小依赖 import 冒烟")
    p_ic.add_argument("forward", nargs=argparse.REMAINDER)
    p_ic.set_defaults(handler=h.cmd_check_import)

    cache = sub.add_parser("cache", help="缓存清理")
    cache_sub = cache.add_subparsers(dest="action", required=True)
    cache_sub.add_parser("clear-global").set_defaults(handler=h.cmd_cache_clear_global)
    cache_sub.add_parser("clear-simulation").set_defaults(handler=h.cmd_cache_clear_simulation)
    cache_sub.add_parser("clear-db").set_defaults(handler=h.cmd_cache_clear_db)
    cache_sub.add_parser("clear-disk").set_defaults(handler=h.cmd_cache_clear_disk)

    db = sub.add_parser("db", help="数据库")
    db_sub = db.add_subparsers(dest="action", required=True)
    p_dbc = db_sub.add_parser("checkpoint", help="DuckDB WAL 合并")
    p_dbc.add_argument(
        "--recover",
        dest="recover_corrupt_wal",
        action="store_true",
        help="WAL 损坏时删除 .wal 后重试",
    )
    p_dbc.set_defaults(handler=h.cmd_db_checkpoint)

    data = sub.add_parser("data", help="开发数据")
    data_sub = data.add_subparsers(dest="action", required=True)
    p_ex = data_sub.add_parser("export-init", help="打包演示数据 zip")
    p_ex.add_argument("forward", nargs=argparse.REMAINDER)
    p_ex.set_defaults(handler=h.cmd_data_export_init)

    userspace = sub.add_parser("userspace", help="userspace 打包")
    us_sub = userspace.add_subparsers(dest="action", required=True)
    p_pu = us_sub.add_parser("package", help="同步 init userspace + zip")
    p_pu.add_argument("--no-zip", action="store_true")
    p_pu.set_defaults(handler=h.cmd_userspace_package)

    pool = sub.add_parser("pool", help="股票池抽样")
    pool_sub = pool.add_subparsers(dest="action", required=True)
    p_sample = pool_sub.add_parser("sample", help="分层抽样 N 只并激活")
    p_sample.add_argument("count", type=int)
    p_sample.add_argument("-v", "--verbose", action="store_true")
    p_sample.set_defaults(handler=h.cmd_pool_sample)
    pool_sub.add_parser("clear", help="取消股票池").set_defaults(handler=h.cmd_pool_clear)

    release = sub.add_parser("release", help="发布准备")
    rel_sub = release.add_subparsers(dest="action", required=True)
    p_pub = rel_sub.add_parser("publish", help="版本发布检查流水线")
    p_pub.add_argument("-v", "--version", required=True, help="目标版本 X.Y.Z 或 vX.Y.Z")
    p_pub.add_argument("--check-only", action="store_true")
    p_pub.add_argument("--skip-tests", action="store_true")
    p_pub.add_argument("--skip-ic", action="store_true")
    p_pub.add_argument("--skip-fed-build", action="store_true")
    p_pub.add_argument("--skip-py39", action="store_true")
    p_pub.add_argument(
        "--package-userspace",
        action="store_true",
        help="检查通过后打包 init userspace",
    )
    p_pub.set_defaults(handler=h.cmd_release_publish)

    return parser


def _epilog() -> str:
    return """
语义命令:
  devcli.py ui run [--kill-first]
  devcli.py ui kill [--ntq-only]
  devcli.py check import
  devcli.py cache clear-global | clear-simulation | clear-db | clear-disk
  devcli.py db checkpoint [--recover]
  devcli.py data export-init
  devcli.py userspace package [--no-zip]
  devcli.py pool sample N | pool clear
  devcli.py release publish -v X.Y.Z [options]

等价缩写:
  -ui -kui -ic -cc -csc -cdc -cmc -dbc -userspace -ex
  -ssl -500 | -ssl -clear   （pool sample / clear）
  -p -vX.Y.Z                （release publish，沿用 publish_prep 解析）
"""


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "forward"):
        args.forward = h.normalize_forward(args.forward or [])
    return args
