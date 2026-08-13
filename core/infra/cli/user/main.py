"""CLI entry orchestration."""

from __future__ import annotations
from core.infra.cmd_layout import i

import logging
import sys
import warnings

from core.infra.cli.user.abbrev import UserAbbrev
from core.infra.cli.user.app import CliApp
from core.infra.cli.user.handlers import UserHandlers
from core.infra.cli.user.parser import UserParser

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
            from core.infra.trace import Trace

            Trace.ask_permission(source="cli")
        except KeyboardInterrupt:
            return 0
        except Exception:
            pass

        try:
            from setup import Setup

            Setup.trace.app_start(entry="cli")
        except Exception:
            pass

        UserHandlers.setup_logging(verbose=args.verbose)

        label = args.command
        app = CliApp(is_verbose=args.verbose)

        try:
            logger.info("=" * 60)
            logger.info(i('play') + "  执行命令: %s", label)
            logger.info("=" * 60)

            UserHandlers.execute(args, app)

            logger.info("")
            logger.info("=" * 60)
            logger.info(f"{i('success')} 命令执行完成")
            logger.info("=" * 60)
            return 0
        except KeyboardInterrupt:
            logger.warning(f"\n{i('warning')}  用户中断执行")
            try:
                from core.infra.db import Db

                Db.duckdb.worker_pool.recover_after_interrupt()
            except Exception as exc:
                logger.warning("DuckDB / worker 中断收尾未完全成功: %s", exc)
            return 0
        except SystemExit as exc:
            code = exc.code
            return int(code) if isinstance(code, int) else 1
        except Exception as exc:
            logger.error(i('error') + " 执行失败: %s", exc)
            if args.verbose:
                import traceback

                traceback.print_exc()
            return 1
