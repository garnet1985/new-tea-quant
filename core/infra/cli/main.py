"""CLI entry orchestration."""

from __future__ import annotations

import logging
import sys
import warnings

from core.infra.cli.abbrev import expand_argv, is_help_argv
from core.infra.cli.app import CliApp
from core.infra.cli.handlers import execute, run_early_command
from core.infra.cli.parser import build_parser, parse_args

logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool = False) -> None:
    """Initialize simple logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def _setup_warnings() -> None:
    warnings.filterwarnings("ignore", category=FutureWarning, module="tushare")
    warnings.filterwarnings(
        "ignore", category=FutureWarning, message=".*fillna.*method.*"
    )
    warnings.filterwarnings("ignore", category=FutureWarning, module="pandas")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="pandas")
    warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="numpy")


def main(argv: list[str] | None = None) -> int:
    _setup_warnings()

    raw = list(argv if argv is not None else sys.argv[1:])
    if is_help_argv(raw):
        build_parser().print_help()
        return 0

    if not raw:
        raw = []

    expanded = expand_argv(raw)
    try:
        args = parse_args(expanded)
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 1

    early = run_early_command(args)
    if early is not None:
        return early

    _setup_logging(verbose=args.verbose)

    label = args.command
    app = CliApp(is_verbose=args.verbose)

    try:
        logger.info("=" * 60)
        logger.info("▶️  执行命令: %s", label)
        logger.info("=" * 60)

        execute(args, app)

        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ 命令执行完成")
        logger.info("=" * 60)
        return 0
    except KeyboardInterrupt:
        logger.warning("\n⚠️  用户中断执行")
        try:
            from core.infra.db.engines.duckdb.process_pool_scope import (
                recover_after_worker_pool_interrupt,
            )

            recover_after_worker_pool_interrupt()
        except Exception as exc:
            logger.warning("DuckDB / worker 中断收尾未完全成功: %s", exc)
        return 0
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 1
    except Exception as exc:
        logger.error("❌ 执行失败: %s", exc)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1
