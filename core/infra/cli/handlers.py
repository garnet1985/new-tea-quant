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
from core.system import system_meta

logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool = False) -> None:
    """Initialize simple logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


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

        _setup_logging(verbose=args.verbose)
        out = getattr(args, "output", None)
        output_path = str(out).strip() if out else None
        return run_export(name, output_path=output_path or None)

    if cmd == "import_strategy":
        path = _strategy_name(getattr(args, "path", None))
        if not path:
            raise SystemExit("import_strategy 需要包路径（例: cli.py im ./pkg.zip）")
        from core.modules.strategy.launcher.package_cli import run_strategy_bundle_import

        _setup_logging(verbose=args.verbose)
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

    from core.infra.system_actions.shortcuts import (
        ScaffoldError,
        scaffold_strategy,
        scaffold_tag,
    )

    _setup_logging(verbose=args.verbose)

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
        dry_run = getattr(args, "dry_run", False)
        if dry_run:
            logger.info("⚠️  DRY RUN 模式：计算结果不会写入数据库")
        app.tag(
            scenario_name=getattr(args, "scenario", None),
            dry_run=dry_run,
            stock_limit=getattr(args, "stock_limit", None),
            profile=getattr(args, "profile", False),
            entities_per_job=getattr(args, "entities_per_job", None),
        )
        return

    if cmd in (
        "scan",
        "strategy_enumerate",
        "strategy_price_factor",
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


def _resolve_strategy_key(name: Optional[str]) -> str:
    from core.modules.strategy.core.services.discovery.discovery_service import DiscoveryService

    explicit = _strategy_name(name)
    if explicit:
        if DiscoveryService.find_strategy(explicit) is None:
            keys = DiscoveryService.list_enabled_keys()
            logger.error("策略不存在或未启用: %s", explicit)
            if keys:
                logger.error("可用 meta.key: %s", ", ".join(sorted(keys)))
            raise SystemExit(1)
        return explicit

    enabled = DiscoveryService.get_enabled_strategies()
    if not enabled:
        logger.error(
            "未指定 --strategy，且 userspace/strategies 下没有 is_enabled=True 的合法策略。"
            "请检查 settings.py 含 meta.key 与 is_enabled=True。"
        )
        raise SystemExit(1)
    if len(enabled) > 1:
        logger.warning(
            "多个启用策略，默认使用 key=%s（%s）；可用 --strategy <meta.key> 指定",
            enabled[0].key,
            enabled[0].unique_relative_path,
        )
    return enabled[0].key


# 兼容旧名
_resolve_enumerate_strategy = _resolve_strategy_key


def _run_strategy_enumerate(args: argparse.Namespace) -> None:
    import time

    from core.modules.strategy import Strategy

    strategy_key = _resolve_strategy_key(getattr(args, "strategy", None))
    force = bool(getattr(args, "force", False))
    stock_count = getattr(args, "stocks", None)

    runtime_settings: dict = {}
    if stock_count is not None:
        runtime_settings["sampling"] = {
            "use_sampling": True,
            "sampling_amount": int(stock_count),
        }

    print("🔢 枚举投资机会…", flush=True)
    print(f"  策略: {strategy_key}", flush=True)
    if stock_count is not None:
        print(f"  采样: {stock_count} 只股票", flush=True)
    else:
        print(
            "  提示: 未传 --stocks 时将按 settings.sampling 抽样（可能数百只，耗时较长）",
            flush=True,
        )
    print("  进度: 5%→15% 为调度探针，之后按 batch 推进；完成后输出结果摘要", flush=True)

    t0 = time.perf_counter()
    result = Strategy.enumerate(
        strategy_key,
        ignore_cache=force,
        runtime_settings=runtime_settings or None,
    )
    wall_sec = time.perf_counter() - t0

    enum_result = result.get("enumerate") if isinstance(result.get("enumerate"), dict) else result

    # 终局摘要统一走 ReportManager.present（entity / slice 相同契约）
    if enum_result.get("output_dir"):
        try:
            from pathlib import Path

            from core.modules.strategy.core.engines.enumerator.shared.report_manager import (
                ReportManager,
            )

            ReportManager.from_output_dir(Path(enum_result["output_dir"])).present()
        except FileNotFoundError as exc:
            logger.warning("展示枚举汇总失败（缺产物）: %s", exc)
            print(f"  success: {enum_result.get('success')}", flush=True)
            print(f"  output_dir: {enum_result.get('output_dir')}", flush=True)
        except Exception as exc:
            logger.warning("展示枚举汇总失败: %s", exc)
            print(f"  success: {enum_result.get('success')}", flush=True)
            print(f"  output_dir: {enum_result.get('output_dir')}", flush=True)
    else:
        print(f"  success: {enum_result.get('success')}", flush=True)
        print(f"  opportunities: {enum_result.get('opportunities_count', 0)}", flush=True)

    print(f"  总耗时(含调度): {wall_sec:.2f}s", flush=True)
    if not enum_result.get("success"):
        failed = enum_result.get("failed_entities") or []
        if failed:
            print(f"  failed: {failed[0].get('error')}")
        raise SystemExit(1)


def _run_strategy_price_factor(args: argparse.Namespace) -> None:
    import time

    from core.modules.strategy import Strategy

    strategy_key = _resolve_strategy_key(getattr(args, "strategy", None))
    force = bool(getattr(args, "force", False))

    print("💹 价格因子回测…", flush=True)
    print(f"  策略: {strategy_key}", flush=True)
    if force:
        print("  --force: 忽略缓存重跑", flush=True)
    print("  依赖: 同指纹枚举产物；缺失时会先补跑枚举", flush=True)

    t0 = time.perf_counter()
    result = Strategy.price_factor(
        strategy_key,
        ignore_cache=force,
    )
    wall_sec = time.perf_counter() - t0

    pf = result.get("price_factor") if isinstance(result.get("price_factor"), dict) else result
    enum_part = result.get("enumerate") if isinstance(result.get("enumerate"), dict) else None
    if enum_part:
        print(
            f"  枚举: success={enum_part.get('success')} version={enum_part.get('version_id')}",
            flush=True,
        )
    summary = pf.get("summary") if isinstance(pf, dict) else {}
    print(f"  output_dir: {pf.get('output_dir')}", flush=True)
    print(f"  version: {pf.get('version_id')}", flush=True)
    print(f"  enum_version: {pf.get('enum_version_id')}", flush=True)
    if summary:
        print(
            "  summary: "
            f"investments={summary.get('total_investments', 0)} "
            f"win_rate={summary.get('win_rate', 0):.2f}% "
            f"avg_roi={summary.get('avg_roi', 0):.4f}",
            flush=True,
        )
    print(f"  success: {pf.get('success')}", flush=True)
    print(f"  总耗时: {wall_sec:.2f}s", flush=True)
    if not pf.get("success", True):
        raise SystemExit(1)


def _run_strategy_portfolio(args: argparse.Namespace) -> None:
    import time

    from core.modules.strategy import Strategy

    strategy_key = _resolve_strategy_key(getattr(args, "strategy", None))
    force = bool(getattr(args, "force", False))

    print("💰 组合回测（portfolio）…", flush=True)
    print(f"  策略: {strategy_key}", flush=True)
    if force:
        print("  --force: 忽略缓存重跑", flush=True)
    print("  依赖: 同指纹枚举产物；缺失时会先补跑枚举", flush=True)

    t0 = time.perf_counter()
    result = Strategy.portfolio(
        strategy_key,
        ignore_cache=force,
    )
    wall_sec = time.perf_counter() - t0

    pf = result.get("portfolio") if isinstance(result.get("portfolio"), dict) else result
    enum_part = result.get("enumerate") if isinstance(result.get("enumerate"), dict) else None
    if enum_part:
        print(
            f"  枚举: success={enum_part.get('success')} version={enum_part.get('version_id')}",
            flush=True,
        )
    summary = pf.get("summary") if isinstance(pf, dict) else {}
    print(f"  output_dir: {pf.get('output_dir')}", flush=True)
    print(f"  version: {pf.get('version_id')}", flush=True)
    print(f"  enum_version: {pf.get('enum_version_id')}", flush=True)
    if summary:
        print(
            "  summary: "
            f"trades={summary.get('total_trades', summary.get('total_investments', 0))} "
            f"total_return={summary.get('total_return', summary.get('roi', 0))}",
            flush=True,
        )
    print(f"  success: {pf.get('success')}", flush=True)
    print(f"  总耗时: {wall_sec:.2f}s", flush=True)
    if not pf.get("success", True):
        raise SystemExit(1)


def _handle_strategy(cmd: str, app: CliApp, args: argparse.Namespace) -> None:
    if cmd == "strategy_enumerate":
        _run_strategy_enumerate(args)
        return

    if cmd == "strategy_price_factor":
        _run_strategy_price_factor(args)
        return

    if cmd == "strategy_portfolio":
        _run_strategy_portfolio(args)
        return

    mgr = app._ensure_strategy_manager()
    name = _strategy_name(getattr(args, "strategy", None))
    force = bool(getattr(args, "force", False))

    if cmd == "scan":
        logger.info("🔍 扫描投资机会...")
        mgr.scan(strategy_name=name, demo=bool(getattr(args, "demo", False)))
        return

    if cmd == "strategy_simulate":
        print("🎮 模拟链路 · PriceFactor → Portfolio …")
        mgr.simulate("full", strategy_name=name, force_refresh=force)
        return

    if cmd == "strategy_analyse":
        logger.info("📊 分析模拟结果...")
        mgr.analyze_simulation_outputs(session_id=getattr(args, "session", None))
        return

    raise SystemExit(f"未知命令: {cmd}")
