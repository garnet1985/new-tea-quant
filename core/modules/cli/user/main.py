"""CLI entry orchestration."""

from __future__ import annotations
from core.infra.cmd_layout import i

import logging
import sys
import warnings

from core.modules.cli.user.abbrev import UserAbbrev
from core.modules.cli.user.app import CliApp
from core.modules.cli.user.handlers import UserHandlers
from core.modules.cli.user.parser import UserParser

logger = logging.getLogger(__name__)


class UserRunner:
    """User CLI main dispatch."""

    @staticmethod
    def _setup_warnings() -> None:
        warnings.filterwarnings("ignore", category=FutureWarning, module="tushare")
        warnings.filterwarnings(
            "ignore", category=FutureWarning, message=".*fillna.*method.*"
        )
        warnings.filterwarnings("ignore", category=FutureWarning, module="pandas")
        warnings.filterwarnings(
            "ignore", category=DeprecationWarning, module="pandas"
        )
        warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")
        warnings.filterwarnings("ignore", category=DeprecationWarning, module="numpy")

    @staticmethod
    def main(argv: list[str] | None = None) -> int:
        UserRunner._setup_warnings()

        raw = list(argv if argv is not None else sys.argv[1:])
        if UserAbbrev.is_help_argv(raw):
            UserParser.build_parser().print_help()
            return 0

        show_help_before_version = not raw
        try:
            args = UserParser.parse_args(raw)
        except SystemExit as exc:
            code = exc.code
            return int(code) if isinstance(code, int) else 1

        if show_help_before_version and args.command == "version":
            UserParser.build_parser().print_help()
            print()

        try:
            from core.infra.trace import Trace

            Trace.send(budget="auto")
        except Exception:
            pass

        early = UserHandlers.run_early_command(args)
        if early is not None:
            return early

        try:
            from core.infra.setup import Setup

            Setup.license.apply_trace_consent()
        except Exception:
            pass

        try:
            from core.modules.cli.user.commands import UserCommands
            from core.infra.setup import Setup

            cmd = str(getattr(args, "command", "") or "")
            if cmd in UserCommands.TRACE_RUN_COMMANDS and not (
                cmd == "tag" and bool(getattr(args, "list", False))
            ):
                command_line = " ".join(["cli.py", *raw]).strip()[:256]
                Setup.trace.app_start(entry="cli", command=command_line)
        except Exception:
            pass

        UserHandlers.setup_logging(verbose=args.verbose)

        label = args.command
        app = CliApp(is_verbose=args.verbose)

        try:
            print("=" * 60, flush=True)
            print(f"{i('play')}  执行命令: {label}", flush=True)
            print("=" * 60, flush=True)

            UserHandlers.execute(args, app)

            print(flush=True)
            print("=" * 60, flush=True)
            print(f"{i('success')} 命令执行完成", flush=True)
            print("=" * 60, flush=True)
            return 0
        except KeyboardInterrupt:
            print(f"\n{i('warning')}  用户中断执行", flush=True)
            try:
                from core.infra.db import Db

                Db.duckdb.worker_pool.recover_after_interrupt()
            except Exception as exc:
                print(f"{i('warning')} DuckDB / worker 中断收尾未完全成功: {exc}", flush=True)
                logger.warning("DuckDB / worker 中断收尾未完全成功", exc_info=True)
            return 0
        except SystemExit as exc:
            code = exc.code
            if isinstance(code, str) and code.strip():
                print(code, flush=True)
                return 1
            return int(code) if isinstance(code, int) else 1
        except Exception as exc:
            print(f"{i('error')} 执行失败: {exc}", flush=True)
            logger.exception("执行失败")
            return 1
