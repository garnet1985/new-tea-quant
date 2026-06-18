"""Dispatch parsed CLI commands to domain services."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from core.infra.cli.app import CliApp
from core.infra.logging.logging_manager import LoggingManager
from core.system import system_meta

logger = logging.getLogger(__name__)


def _strategy_name(raw: object) -> Optional[str]:
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def run_app_update() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    updater_dir = None
    for candidate in (
        repo_root / "userspace" / "system" / "updater",
        repo_root / "setup" / "updater",
    ):
        if (candidate / "upgrade_entry.py").is_file():
            updater_dir = candidate
            break
    if updater_dir is None:
        sys.stderr.write(
            "未找到升级器（userspace/system/updater 或 setup/updater）。"
            "请先完成 init userspace 或从仓库安装 updater。\n"
        )
        return 1

    upd_path = str(updater_dir.resolve())
    if upd_path not in sys.path:
        sys.path.insert(0, upd_path)

    from upgrade_entry import run_interactive_upgrade  # noqa: E402

    assume_yes = os.environ.get("NTQ_UPDATE_ASSUME_YES", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    return run_interactive_upgrade(repo_root, assume_yes=assume_yes)


def run_early_command(args: argparse.Namespace) -> int | None:
    new_path = _strategy_name(getattr(args, "new_path", None))
    if new_path:
        cmd = getattr(args, "command", None)
        if cmd == "tag":
            return _run_scaffold("tag", new_path, args)
        return _run_scaffold("strategy", new_path, args)

    cmd = args.command

    if cmd == "update":
        return run_app_update()

    if cmd == "version":
        print(f"NTQ Core Version: {system_meta.version}")
        print(f"Release Date: {system_meta.release_date}")
        return 0

    if cmd == "export_strategy":
        name = _strategy_name(getattr(args, "name", None))
        if not name:
            raise SystemExit("export_strategy 需要名称（例: cli.py ex example）")
        from core.modules.strategy.launcher.package_cli import run_export

        LoggingManager.setup_logging()
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        out = getattr(args, "output", None)
        output_path = str(out).strip() if out else None
        return run_export(name, output_path=output_path or None)

    if cmd == "import_strategy":
        path = _strategy_name(getattr(args, "path", None))
        if not path:
            raise SystemExit("import_strategy 需要包路径（例: cli.py im ./pkg.zip）")
        from core.modules.strategy.launcher.package_cli import run_strategy_bundle_import

        LoggingManager.setup_logging()
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        return run_strategy_bundle_import(
            path,
            force=bool(getattr(args, "force", False)),
            skip_existing=bool(getattr(args, "skip_existing", False)),
            dry_run=bool(getattr(args, "dry_run", False)),
        )

    return None


def _run_scaffold(kind: str, raw_path: object, args: argparse.Namespace) -> int:
    path = str(raw_path or "").strip()
    if not path:
        raise SystemExit(f"new_{kind} 需要目标路径")

    from core.infra.userspace.scaffold import ScaffoldError, scaffold_strategy, scaffold_tag

    LoggingManager.setup_logging()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        if kind == "tag":
            result = scaffold_tag(path)
            label = "Tag 场景"
        else:
            result = scaffold_strategy(path)
            label = "策略"
        logger.info("✅ 已新建 %s: %s", label, result.key)
        logger.info("   目录: %s", result.dest)
        logger.info("   请编辑 settings.py 与 worker，然后运行回测或打标。")
        return 0
    except ScaffoldError as exc:
        logger.error("❌ %s", exc)
        return 1


def execute(args: argparse.Namespace, app: CliApp) -> None:
    cmd = args.command

    if cmd == "renew":
        _handle_renew(app, args)
        return

    if cmd == "export_adj_factor":
        logger.info("📤 手动导出复权因子事件季度 CSV...")
        app.export_adj_factor_csv(base_date=getattr(args, "base_date", None))
        return

    if cmd == "tag":
        if getattr(args, "new_path", None):
            raise SystemExit("新建 Tag 请使用: cli.py t -n PATH")
        logger.info("🏷️  执行标签计算...")
        app.tag(scenario_name=getattr(args, "scenario", None))
        return

    if cmd in (
        "scan",
        "strategy_enumerate",
        "strategy_price_factor",
        "strategy_capital_allocate",
        "strategy_portfolio",
        "strategy_simulate",
        "strategy_analyse",
    ):
        _handle_strategy(cmd, app, args)
        return

    raise SystemExit(f"未知命令: {cmd}")


def _handle_renew(app: CliApp, args: argparse.Namespace) -> None:
    source = _strategy_name(getattr(args, "source", None))
    force = bool(getattr(args, "force", False))

    if source and source.lower() == "list":
        from core.modules.data_source.data_source_manager import DataSourceManager

        logger.info("%s", DataSourceManager.format_renew_targets_help())
        return

    if source:
        logger.info("🔄 更新数据: %s%s", source, " [force refresh]" if force else "")
    else:
        logger.info("🔄 更新全部已启用数据源%s", " [force]" if force else "")

    try:
        asyncio.run(app.renew_data(table_name=source, force=force))
    except ValueError as exc:
        logger.error("❌ %s", exc)
        raise SystemExit(1) from exc


def _handle_strategy(cmd: str, app: CliApp, args: argparse.Namespace) -> None:
    mgr = app._ensure_strategy_manager()
    name = _strategy_name(getattr(args, "strategy", None))
    force = bool(getattr(args, "force", False))

    if cmd == "scan":
        logger.info("🔍 扫描投资机会...")
        mgr.scan(strategy_name=name, demo=bool(getattr(args, "demo", False)))
        return

    if cmd == "strategy_enumerate":
        print("🔢 枚举投资机会…")
        mgr.simulate(
            "enumerate",
            strategy_name=name,
            force_refresh=force,
            stock_count=getattr(args, "stocks", None),
        )
        return

    if cmd == "strategy_price_factor":
        mgr.simulate("price_factor", strategy_name=name, force_refresh=force)
        return

    if cmd in ("strategy_capital_allocate", "strategy_portfolio"):
        mgr.simulate("capital_allocation", strategy_name=name, force_refresh=force)
        return

    if cmd == "strategy_simulate":
        print("🎮 模拟链路 · PriceFactor → CapitalAllocation …")
        mgr.simulate("full", strategy_name=name, force_refresh=force)
        return

    if cmd == "strategy_analyse":
        logger.info("📊 分析模拟结果...")
        mgr.analyze_simulation_outputs(session_id=getattr(args, "session", None))
        return

    raise SystemExit(f"未知命令: {cmd}")
