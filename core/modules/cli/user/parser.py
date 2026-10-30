"""Argparse for flat ``command_name`` CLI."""

from __future__ import annotations

import argparse

from core.modules.cli.user.commands import UserCommands
from core.modules.cli.user.help_text import CLI_COMMAND_REFERENCE
from core.modules.cli.shared.help_format import HelpTextOnlyParser

class UserParser:
    """User CLI argparse builder / parser."""

    @staticmethod
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

    @staticmethod
    def build_parser() -> argparse.ArgumentParser:
        parser = HelpTextOnlyParser(
            prog="cli.py",
            help_text=CLI_COMMAND_REFERENCE,
            parents=[UserParser._GLOBAL_FLAGS],
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="开发日志（DEBUG）。默认不输出，只保留命令结果和警告",
        )

        sub = parser.add_subparsers(
            dest="command",
            required=False,
            metavar="COMMAND",
            parser_class=argparse.ArgumentParser,
        )

        UserParser._p_scan(sub)
        UserParser._p_strategy_enumerate(sub)
        UserParser._p_strategy_price_factor(sub)
        UserParser._p_strategy_portfolio(sub)
        UserParser._p_strategy_decision(sub)
        UserParser._p_strategy_decision_list(sub)
        UserParser._p_strategy_decision_delete(sub)
        UserParser._p_strategy_simulate(sub)
        UserParser._p_strategy_attribute_enumerate(sub)
        UserParser._p_strategy_attribute_price(sub)
        UserParser._p_strategy_attribute_portfolio(sub)
        UserParser._p_strategy_rolling(sub)
        UserParser._p_strategy_delete_version(sub)
        UserParser._p_renew(sub)
        UserParser._p_list(sub)
        UserParser._p_export_adj_factor(sub)
        UserParser._p_tag(sub)
        UserParser._p_series_relation(sub)
        UserParser._p_agent(sub)
        UserParser._p_export_strategy(sub)
        UserParser._p_import_strategy(sub)
        UserParser._p_import_data(sub)
        UserParser._p_update(sub)
        UserParser._p_version(sub)

        return parser

    @staticmethod
    def _add_strategy_target(p: argparse.ArgumentParser) -> None:
        p.add_argument("--strategy", type=str, default=None)

    @staticmethod
    def _cmd(sub: argparse._SubParsersAction, name: str, **kwargs: object) -> argparse.ArgumentParser:
        return sub.add_parser(name, parents=[UserParser._GLOBAL_FLAGS], **kwargs)

    @staticmethod
    def _p_scan(sub: argparse._SubParsersAction) -> None:
        p = UserParser._cmd(sub, "scan", aliases=UserCommands.aliases_for("scan"), help="扫描当前投资机会")
        UserParser._add_strategy_target(p)
        p.add_argument("--demo", action="store_true", help="demo 模式")

    @staticmethod
    def _p_strategy_enumerate(sub: argparse._SubParsersAction) -> None:
        p = UserParser._cmd(
            sub,
            "strategy_enumerate",
            aliases=UserCommands.aliases_for("strategy_enumerate"),
            help="机会盘点（历史命中扫描）",
        )
        UserParser._add_strategy_target(p)
        p.add_argument("--stocks", type=int, default=None, help="测试股票数量")

    @staticmethod
    def _p_strategy_price_factor(sub: argparse._SubParsersAction) -> None:
        p = UserParser._cmd(
            sub,
            "strategy_price_factor",
            aliases=UserCommands.aliases_for("strategy_price_factor"),
            help="价格因子回放模拟",
        )
        UserParser._add_strategy_target(p)

    @staticmethod
    def _p_strategy_portfolio(sub: argparse._SubParsersAction) -> None:
        p = UserParser._cmd(
            sub,
            "strategy_portfolio",
            aliases=UserCommands.aliases_for("strategy_portfolio"),
            help="组合/资金回测（portfolio）",
        )
        UserParser._add_strategy_target(p)

    @staticmethod
    def _add_decision_flags(p: argparse.ArgumentParser, *, require_session: bool = False) -> None:
        UserParser._add_strategy_target(p)
        p.add_argument(
            "--version",
            type=str,
            default=None,
            help="回测 version id（默认当前 settings.py 命中的 vid，与 so 相同）",
        )
        p.add_argument(
            "--session",
            dest="session_id",
            type=str,
            default=None,
            required=require_session,
            help="决策者会话 id（该 version 下的 {dm_id}）",
        )

    @staticmethod
    def _p_strategy_decision(sub: argparse._SubParsersAction) -> None:
        p = UserParser._cmd(
            sub,
            "strategy_decision",
            aliases=UserCommands.aliases_for("strategy_decision"),
            help="进入决策者模式（SQL REPL）",
        )
        UserParser._add_decision_flags(p)
        p.add_argument(
            "--new-session",
            action="store_true",
            help="无论有几局未完成都新开一局（不要用全局 -n）",
        )

    @staticmethod
    def _p_strategy_decision_list(sub: argparse._SubParsersAction) -> None:
        p = UserParser._cmd(
            sub,
            "strategy_decision_list",
            aliases=UserCommands.aliases_for("strategy_decision_list"),
            help="列出该 version 下的决策者会话",
        )
        UserParser._add_decision_flags(p)

    @staticmethod
    def _p_strategy_decision_delete(sub: argparse._SubParsersAction) -> None:
        p = UserParser._cmd(
            sub,
            "strategy_decision_delete",
            aliases=UserCommands.aliases_for("strategy_decision_delete"),
            help="删除一局决策者存档",
        )
        UserParser._add_decision_flags(p, require_session=True)

    @staticmethod
    def _p_strategy_simulate(sub: argparse._SubParsersAction) -> None:
        p = UserParser._cmd(
            sub,
            "strategy_simulate",
            aliases=UserCommands.aliases_for("strategy_simulate"),
            help="一次跑完机会盘点、价格和资金回测",
        )
        UserParser._add_strategy_target(p)

    @staticmethod
    def _p_strategy_attribute_enumerate(sub: argparse._SubParsersAction) -> None:
        p = UserParser._cmd(
            sub,
            "strategy_attribute_enumerate",
            aliases=UserCommands.aliases_for("strategy_attribute_enumerate"),
            help="机会盘点层归因（读 attribution.py；须先 se）",
        )
        UserParser._add_strategy_target(p)

    @staticmethod
    def _p_strategy_attribute_price(sub: argparse._SubParsersAction) -> None:
        p = UserParser._cmd(
            sub,
            "strategy_attribute_price",
            aliases=UserCommands.aliases_for("strategy_attribute_price"),
            help="价格层归因（读 attribution.py；须先 sp）",
        )
        UserParser._add_strategy_target(p)

    @staticmethod
    def _p_strategy_attribute_portfolio(sub: argparse._SubParsersAction) -> None:
        p = UserParser._cmd(
            sub,
            "strategy_attribute_portfolio",
            aliases=UserCommands.aliases_for("strategy_attribute_portfolio"),
            help="组合层归因（读 attribution.py；须先 so）",
        )
        UserParser._add_strategy_target(p)

    @staticmethod
    def _p_strategy_rolling(sub: argparse._SubParsersAction) -> None:
        p = UserParser._cmd(
            sub,
            "strategy_rolling",
            aliases=UserCommands.aliases_for("strategy_rolling"),
            help="滚动对照（读 rolling.py；须先完成机会盘点、价格和资金回测）",
        )
        UserParser._add_strategy_target(p)

    @staticmethod
    def _add_strategy_version_spec(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--strategy",
            type=str,
            required=True,
            help="策略:版本，例如 rsi_v1:3 或 demo/foo:v3",
        )

    @staticmethod
    def _p_strategy_delete_version(sub: argparse._SubParsersAction) -> None:
        p = UserParser._cmd(
            sub,
            "strategy_delete_version",
            aliases=UserCommands.aliases_for("strategy_delete_version"),
            help="删除指定策略的一份回测产物（settings.py 不动）",
        )
        UserParser._add_strategy_version_spec(p)

    @staticmethod
    def _p_list(sub: argparse._SubParsersAction) -> None:
        p = UserParser._cmd(
            sub,
            "list",
            aliases=UserCommands.aliases_for("list"),
            help="列出可用选项（catalog：stock.area / stock.industry / …）",
        )
        p.add_argument(
            "resource",
            nargs="?",
            default=None,
            help="如 stock.area；省略则打印可用 resource",
        )
        p.add_argument(
            "--json",
            action="store_true",
            help="JSON 输出",
        )

    @staticmethod
    def _p_renew(sub: argparse._SubParsersAction) -> None:
        p = UserParser._cmd(sub, "renew", aliases=UserCommands.aliases_for("renew"), help="更新 data source")
        p.add_argument(
            "source",
            nargs="?",
            default=None,
            metavar="SOURCE",
            help="表名或 key；省略=全部；list 列出目标",
        )
        p.add_argument(
            "--json",
            action="store_true",
            help="与 list 合用，输出任务栏 JSON",
        )
        p.add_argument(
            "--clear-logs",
            action="store_true",
            help="删除已结束的运行状态目录，留下正在跑的那一次",
        )

    @staticmethod
    def _p_export_adj_factor(sub: argparse._SubParsersAction) -> None:
        p = sub.add_parser("export_adj_factor", help="导出复权因子事件 CSV")
        p.add_argument("--base-date", dest="base_date", type=str, default=None)

    @staticmethod
    def _p_tag(sub: argparse._SubParsersAction) -> None:
        p = UserParser._cmd(
            sub,
            "tag",
            aliases=UserCommands.aliases_for("tag"),
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
            "--entity-limit",
            type=int,
            default=None,
            metavar="N",
            help="只跑前 N 个实体（试验用）",
        )

    @staticmethod
    def _p_series_relation(sub: argparse._SubParsersAction) -> None:
        p = UserParser._cmd(
            sub,
            "series_relation",
            aliases=UserCommands.aliases_for("series_relation"),
            help="多序列并置比较（``srel``；配置在 extensions/series_relation）",
        )
        p.add_argument(
            "key",
            nargs="?",
            default=None,
            metavar="KEY",
            help="meta.key 或相对路径；与 --list 互斥",
        )
        p.add_argument(
            "--list",
            action="store_true",
            help="列出已发现的场景并退出",
        )

    @staticmethod
    def _p_agent(sub: argparse._SubParsersAction) -> None:
        p = UserParser._cmd(
            sub,
            "agent",
            aliases=UserCommands.aliases_for("agent"),
            help="NTQ 助理（对话 / 偏好 / 设置；``a``）",
        )
        p.add_argument(
            "message",
            nargs="?",
            default=None,
            metavar="MESSAGE",
            help="发给助理的一句话（与下方管理开关互斥）",
        )
        p.add_argument(
            "--provider",
            dest="agent_provider",
            type=str,
            default=None,
            metavar="ID",
            help="本轮 Provider（ntq 或已配置的自备 id）；省略用设置页默认",
        )
        p.add_argument(
            "--session",
            dest="agent_session",
            type=str,
            default=None,
            metavar="ID",
            help="会话名（默认 default）",
        )
        exclusive = p.add_mutually_exclusive_group()
        exclusive.add_argument(
            "--tools",
            dest="agent_tools",
            action="store_true",
            help="列出已登记工具",
        )
        exclusive.add_argument(
            "--clear",
            dest="agent_clear",
            action="store_true",
            help="清空本机会话（不删跨会话偏好）",
        )
        exclusive.add_argument(
            "--prefs",
            dest="agent_prefs",
            action="store_true",
            help="列出跨会话偏好",
        )
        exclusive.add_argument(
            "--remember",
            dest="agent_remember",
            type=str,
            default=None,
            metavar="RULE",
            help="追加一条跨会话偏好",
        )
        exclusive.add_argument(
            "--forget",
            dest="agent_forget",
            type=str,
            default=None,
            metavar="RULE",
            help="删除一条跨会话偏好",
        )
        exclusive.add_argument(
            "--settings",
            dest="agent_settings",
            action="store_true",
            help="显示 Agent 产品设置",
        )
        exclusive.add_argument(
            "--set-provider",
            dest="agent_set_provider",
            type=str,
            default=None,
            metavar="ID",
            help="写入默认 Provider",
        )
        exclusive.add_argument(
            "--set-context",
            dest="agent_set_context",
            type=str,
            default=None,
            metavar="TEXT",
            help="写入补充说明（空字符串清空）",
        )

    @staticmethod
    def _p_export_strategy(sub: argparse._SubParsersAction) -> None:
        p = UserParser._cmd(
            sub,
            "export_strategy",
            aliases=UserCommands.aliases_for("export_strategy"),
            help="导出策略交流包（zip）",
        )
        p.add_argument("name", nargs="?", default=None, metavar="NAME")
        p.add_argument("-o", "--output", dest="output", type=str, default=None)

    @staticmethod
    def _p_import_strategy(sub: argparse._SubParsersAction) -> None:
        p = UserParser._cmd(
            sub,
            "import_strategy",
            aliases=UserCommands.aliases_for("import_strategy"),
            help="导入策略交流包",
        )
        p.add_argument("path", nargs="?", default=None, metavar="PATH")
        p.add_argument("--skip-existing", action="store_true")
        p.add_argument("--dry-run", action="store_true")

    @staticmethod
    def _p_import_data(sub: argparse._SubParsersAction) -> None:
        UserParser._cmd(
            sub,
            "import_data",
            aliases=UserCommands.aliases_for("import_data"),
            help="导入 initialization/data 下唯一 zip 数据包（-f 强制全量重导）",
        )

    @staticmethod
    def _p_update(sub: argparse._SubParsersAction) -> None:
        sub.add_parser("update", aliases=UserCommands.aliases_for("update"), help="检查并升级 core")

    @staticmethod
    def _p_version(sub: argparse._SubParsersAction) -> None:
        sub.add_parser("version", aliases=UserCommands.aliases_for("version"), help="显示 core 版本")

    @staticmethod
    def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
        from core.modules.cli.user.abbrev import UserAbbrev

        expanded = UserAbbrev.expand_argv(argv or [])
        parser = UserParser.build_parser()
        args = parser.parse_args(expanded)

        if getattr(args, "new_path", None):
            return args

        if args.command is None:
            args.command = UserCommands.DEFAULT_COMMAND
        return args

UserParser._GLOBAL_FLAGS = UserParser._global_flags_parser()
