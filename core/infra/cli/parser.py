"""Argparse for flat ``command_name`` CLI."""

from __future__ import annotations

import argparse

from core.infra.cli.commands import DEFAULT_COMMAND, aliases_for
from core.infra.cli.help_text import CLI_COMMAND_REFERENCE


def _global_flags_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="强制刷新 / 重算 / 覆盖（全局）",
    )
    p.add_argument(
        "-n",
        "--new",
        dest="new_path",
        metavar="PATH",
        default=None,
        help="从模版新建到 PATH（默认策略；``t -n PATH`` 为 Tag 场景）",
    )
    return p


_GLOBAL_FLAGS = _global_flags_parser()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="NTQ — 数据更新、策略扫描、模拟、分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_epilog(),
        parents=[_GLOBAL_FLAGS],
    )
    parser.add_argument("--verbose", action="store_true", help="详细日志（DEBUG）")

    sub = parser.add_subparsers(dest="command", required=False)

    _p_scan(sub)
    _p_strategy_enumerate(sub)
    _p_strategy_price_factor(sub)
    _p_strategy_portfolio(sub)
    _p_strategy_simulate(sub)
    _p_strategy_analyse(sub)
    _p_renew(sub)
    _p_export_adj_factor(sub)
    _p_tag(sub)
    _p_export_strategy(sub)
    _p_import_strategy(sub)
    _p_update(sub)
    _p_version(sub)

    return parser


def _add_strategy_target(p: argparse.ArgumentParser) -> None:
    p.add_argument("--strategy", type=str, default=None)


def _cmd(sub: argparse._SubParsersAction, name: str, **kwargs: object) -> argparse.ArgumentParser:
    return sub.add_parser(name, parents=[_GLOBAL_FLAGS], **kwargs)


def _p_scan(sub: argparse._SubParsersAction) -> None:
    p = _cmd(sub, "scan", aliases=aliases_for("scan"), help="扫描当前投资机会")
    _add_strategy_target(p)
    p.add_argument("--demo", action="store_true", help="demo 模式")


def _p_strategy_enumerate(sub: argparse._SubParsersAction) -> None:
    p = _cmd(
        sub,
        "strategy_enumerate",
        aliases=aliases_for("strategy_enumerate"),
        help="枚举投资机会",
    )
    _add_strategy_target(p)
    p.add_argument("--stocks", type=int, default=None, help="测试股票数量")


def _p_strategy_price_factor(sub: argparse._SubParsersAction) -> None:
    p = _cmd(
        sub,
        "strategy_price_factor",
        aliases=aliases_for("strategy_price_factor"),
        help="价格因子回放模拟",
    )
    _add_strategy_target(p)


def _p_strategy_portfolio(sub: argparse._SubParsersAction) -> None:
    p = _cmd(
        sub,
        "strategy_portfolio",
        aliases=aliases_for("strategy_portfolio"),
        help="组合/资金回测（portfolio）",
    )
    _add_strategy_target(p)


def _p_strategy_simulate(sub: argparse._SubParsersAction) -> None:
    p = _cmd(
        sub,
        "strategy_simulate",
        aliases=aliases_for("strategy_simulate"),
        help="完整模拟链路（price → portfolio）",
    )
    _add_strategy_target(p)


def _p_strategy_analyse(sub: argparse._SubParsersAction) -> None:
    p = _cmd(
        sub,
        "strategy_analyse",
        aliases=aliases_for("strategy_analyse"),
        help="分析模拟结果",
    )
    p.add_argument("--session", type=str, default=None)


def _p_renew(sub: argparse._SubParsersAction) -> None:
    p = _cmd(sub, "renew", aliases=aliases_for("renew"), help="更新 data source")
    p.add_argument(
        "source",
        nargs="?",
        default=None,
        metavar="SOURCE",
        help="表名或 key；省略=全部；list 列出目标",
    )


def _p_export_adj_factor(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("export_adj_factor", help="导出复权因子事件 CSV")
    p.add_argument("--base-date", dest="base_date", type=str, default=None)


def _p_tag(sub: argparse._SubParsersAction) -> None:
    p = _cmd(
        sub,
        "tag",
        aliases=aliases_for("tag"),
        help="执行标签计算（``t -n PATH`` 为从模版新建 Tag 到 PATH）",
    )
    p.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="tag 路径或 meta.key；省略则跑全部已启用",
    )
    p.add_argument(
        "--list",
        action="store_true",
        help="列出已发现的 tag 并退出",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="只计算不落库（与 settings.calculation.is_dry_run 为 OR）",
    )
    p.add_argument(
        "--stock-limit",
        type=int,
        default=None,
        metavar="N",
        help="只跑前 N 个实体（试验用）",
    )


def _p_export_strategy(sub: argparse._SubParsersAction) -> None:
    p = _cmd(
        sub,
        "export_strategy",
        aliases=aliases_for("export_strategy"),
        help="导出策略交流包（zip）",
    )
    p.add_argument("name", nargs="?", default=None, metavar="NAME")
    p.add_argument("-o", "--output", dest="output", type=str, default=None)


def _p_import_strategy(sub: argparse._SubParsersAction) -> None:
    p = _cmd(
        sub,
        "import_strategy",
        aliases=aliases_for("import_strategy"),
        help="导入策略交流包",
    )
    p.add_argument("path", nargs="?", default=None, metavar="PATH")
    p.add_argument("--skip-existing", action="store_true")
    p.add_argument("--dry-run", action="store_true")


def _p_update(sub: argparse._SubParsersAction) -> None:
    sub.add_parser("update", aliases=aliases_for("update"), help="检查并升级 core")


def _p_version(sub: argparse._SubParsersAction) -> None:
    sub.add_parser("version", aliases=aliases_for("version"), help="显示 core 版本")


def _epilog() -> str:
    return "\n" + CLI_COMMAND_REFERENCE + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    from core.infra.cli.abbrev import expand_argv

    expanded = expand_argv(argv or [])
    parser = build_parser()
    args = parser.parse_args(expanded)

    if getattr(args, "new_path", None):
        return args

    if args.command is None:
        args.command = DEFAULT_COMMAND
    return args
