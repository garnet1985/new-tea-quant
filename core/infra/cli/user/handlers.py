"""Dispatch parsed CLI commands to domain services."""

from __future__ import annotations
from core.infra.cmd_layout import i

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from core.infra.cli.shared.env import CliEnv
from core.infra.cli.user.app import CliApp
from core.system import system_meta

logger = logging.getLogger(__name__)


class UserHandlers:
    """User CLI command dispatch."""

    @staticmethod
    def setup_logging(verbose: bool = False) -> None:
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    @staticmethod
    def _strategy_name(raw: object) -> Optional[str]:
        if raw is None:
            return None
        text = str(raw).strip()
        return text or None

    @staticmethod
    def parse_strategy_version_spec(raw: object) -> tuple[str, int]:
        """``rsi_v1:3`` / ``demo/foo:v3`` → (策略, version int)。按最后一个冒号切开。"""
        from core.modules.strategy.core.helpers.version_id import WorkbenchVersionId

        text = str(raw or "").strip()
        if ":" not in text:
            raise ValueError("必须写成 策略:版本，例如 rsi_v1:3")
        name, _, vid = text.rpartition(":")
        name = name.strip()
        sid = WorkbenchVersionId.parse(vid)
        if not name or sid is None:
            raise ValueError("必须写成 策略:版本，例如 rsi_v1:3")
        return name, sid

    @staticmethod
    def run_app_update() -> int:
        repo_root = Path(__file__).resolve().parents[4]
        updater_dir = repo_root / "userspace" / "system" / "updater"
        if not (updater_dir / "upgrade_entry.py").is_file():
            sys.stderr.write(
                "未找到升级器 userspace/system/updater。"
                "请先完成安装（init userspace）。\n"
            )
            return 1

        upd_path = str(updater_dir.resolve())
        if upd_path not in sys.path:
            sys.path.insert(0, upd_path)

        from upgrade_entry import run_interactive_upgrade  # noqa: E402

        assume_yes = CliEnv.is_truthy(CliEnv.UPDATE_ASSUME_YES)
        return run_interactive_upgrade(repo_root, assume_yes=assume_yes)

    @staticmethod
    def run_early_command(args: argparse.Namespace) -> int | None:
        new_path = UserHandlers._strategy_name(getattr(args, "new_path", None))
        if new_path:
            cmd = getattr(args, "command", None)
            if cmd == "tag":
                return UserHandlers._run_scaffold("tag", new_path, args)
            return UserHandlers._run_scaffold("strategy", new_path, args)

        cmd = args.command

        if cmd == "update":
            return UserHandlers.run_app_update()

        if cmd == "version":
            print(f"NTQ Core Version: {system_meta.version}")
            print(f"Release Date: {system_meta.release_date}")
            return 0

        if cmd == "export_strategy":
            name = UserHandlers._strategy_name(getattr(args, "name", None))
            if not name:
                raise SystemExit("export_strategy 需要名称（例: cli.py ex example）")
            from core.modules.strategy import Strategy

            UserHandlers.setup_logging(verbose=args.verbose)
            out = getattr(args, "output", None)
            output_path = str(out).strip() if out else None
            return Strategy.export_package(name, output_path=output_path or None)

        if cmd == "import_strategy":
            path = UserHandlers._strategy_name(getattr(args, "path", None))
            if not path:
                raise SystemExit("import_strategy 需要包路径（例: cli.py im ./pkg.zip）")
            from core.modules.strategy import Strategy

            UserHandlers.setup_logging(verbose=args.verbose)
            return Strategy.import_package(
                path,
                force=bool(getattr(args, "force", False)),
                skip_existing=bool(getattr(args, "skip_existing", False)),
                dry_run=bool(getattr(args, "dry_run", False)),
            )

        if cmd == "import_data":
            from core.infra.setup import Setup

            UserHandlers.setup_logging(verbose=args.verbose)
            force = bool(getattr(args, "force", False))
            logger.info(
                i("ongoing") + " 导入 initialization/data 数据包%s",
                " [force]" if force else "",
            )
            return Setup.runtime.import_init_data(force=force)

        return None

    @staticmethod
    def _run_scaffold(kind: str, raw_path: object, args: argparse.Namespace) -> int:
        path = str(raw_path or "").strip()
        if not path:
            raise SystemExit(f"new_{kind} 需要目标路径")

        from core.infra.cli.user.scripts.create_from_template import CreateFromTemplate

        UserHandlers.setup_logging(verbose=args.verbose)

        try:
            if kind == "tag":
                result = CreateFromTemplate.create_tag(path)
                label = "Tag 场景"
            else:
                result = CreateFromTemplate.create_strategy(path)
                label = "策略"
            logger.info(i('success') + " 已新建 %s: %s", label, result.key)
            logger.info("   目录: %s", result.dest)
            logger.info("   请编辑 settings.py 与 worker，然后运行回测或打标。")
            return 0
        except CreateFromTemplate.Error as exc:
            logger.error(i('error') + " %s", exc)
            return 1

    @staticmethod
    def execute(args: argparse.Namespace, app: CliApp) -> None:
        cmd = args.command

        if cmd == "renew":
            UserHandlers._handle_renew(app, args)
            return

        if cmd == "export_adj_factor":
            logger.info(f"{i('upload')} 手动导出复权因子事件季度 CSV...")
            app.export_adj_factor_csv(base_date=getattr(args, "base_date", None))
            return

        if cmd == "tag":
            if getattr(args, "new_path", None):
                raise SystemExit("新建 Tag 请使用: cli.py t -n PATH")
            if getattr(args, "list", False):
                names = app.list_tags(enabled_only=False)
                if not names:
                    print("未发现 tag（检查 userspace/extensions/tags 下 settings.py + tag.py）")
                    raise SystemExit(1)
                print("可用 tag:")
                for name in names:
                    print(f"  - {name}")
                return
            logger.info(f"{i('tag')}  执行标签计算...")
            dry_run = getattr(args, "dry_run", False)
            if dry_run:
                logger.info(f"{i('warning')}  DRY RUN 模式：计算结果不会写入数据库")
            app.tag(
                scenario_name=getattr(args, "scenario", None),
                dry_run=dry_run,
                entity_limit=getattr(args, "entity_limit", None),
            )
            return

        if cmd in (
            "scan",
            "strategy_enumerate",
            "strategy_price_factor",
            "strategy_portfolio",
            "strategy_simulate",
            "strategy_analyze",
            "strategy_delete_version",
            "strategy_pin_version",
            "strategy_unpin_version",
        ):
            UserHandlers._handle_strategy(cmd, app, args)
            return

        raise SystemExit(f"未知命令: {cmd}")

    @staticmethod
    def _handle_renew(app: CliApp, args: argparse.Namespace) -> None:
        source = UserHandlers._strategy_name(getattr(args, "source", None))
        force = bool(getattr(args, "force", False))

        if source and source.lower() == "list":
            from core.modules.data_source import DataSourceManager

            logger.info("%s", DataSourceManager.format_renew_targets_help())
            return

        if source:
            logger.info(i('ongoing') + " 更新数据: %s%s", source, " [force refresh]" if force else "")
        else:
            logger.info(i('ongoing') + " 更新全部已启用数据源%s", " [force]" if force else "")

        try:
            asyncio.run(app.renew_data(table_name=source, force=force))
        except ValueError as exc:
            logger.error(i('error') + " %s", exc)
            raise SystemExit(1) from exc

    @staticmethod
    def _resolve_strategy_key(name: Optional[str]) -> str:
        from core.modules.strategy import Strategy

        explicit = UserHandlers._strategy_name(name)
        if explicit:
            info = Strategy.find(explicit, enabled_only=True)
            if info is None:
                keys = Strategy.list_enabled_keys()
                logger.error("策略不存在或未启用: %s", explicit)
                if keys:
                    logger.error("可用 meta.key: %s", ", ".join(sorted(keys)))
                raise SystemExit(1)
            return str(info.get("key") or explicit)

        enabled = Strategy.list_strategy_infos(enabled_only=True)
        if not enabled:
            logger.error(
                "未指定 --strategy，且 userspace/strategies 下没有 is_enabled=True 的合法策略。"
                "请检查 settings.py 含 meta.key 与 is_enabled=True。"
            )
            raise SystemExit(1)
        if len(enabled) > 1:
            logger.warning(
                "多个启用策略，默认使用 key=%s（%s）；可用 --strategy <meta.key> 指定",
                enabled[0].get("key"),
                enabled[0].get("unique_relative_path"),
            )
        return str(enabled[0].get("key") or enabled[0].get("unique_relative_path"))

    @staticmethod
    def _print_analysis_from_step(step_result: dict) -> None:
        analysis = step_result.get("analysis") if isinstance(step_result, dict) else None
        if isinstance(analysis, dict) and not analysis.get("skipped"):
            print(f"  归因: report={analysis.get('report_path')}", flush=True)
        elif isinstance(analysis, dict) and analysis.get("reason") not in (None, "disabled"):
            print(f"  归因: skip ({analysis.get('reason')})", flush=True)

    @staticmethod
    def _print_simulate_version(result: dict, step_key: str) -> None:
        """Print disk ``version_id`` + step ``output_dir`` (``se`` / ``sp`` / ``so``)."""
        if not isinstance(result, dict):
            return
        step = result.get(step_key)
        vid = str(result.get("version_id") or "").strip()
        if isinstance(step, dict):
            vid = vid or str(step.get("version_id") or "").strip()
            out_dir = str(step.get("output_dir") or "").strip()
            if vid:
                print(f"  version_id: {vid}", flush=True)
            if out_dir:
                print(f"  output_dir: {out_dir}", flush=True)
        elif vid:
            print(f"  version_id: {vid}", flush=True)

    @staticmethod
    def _run_strategy_enumerate(args: argparse.Namespace) -> None:
        import time

        from core.modules.strategy import Strategy

        strategy_key = UserHandlers._resolve_strategy_key(getattr(args, "strategy", None))
        force = bool(getattr(args, "force", False))
        stock_count = getattr(args, "stocks", None)

        runtime_settings: dict = {}
        if stock_count is not None:
            runtime_settings["sampling"] = {
                "use_sampling": True,
                "sampling_amount": int(stock_count),
            }

        print(f"{i('numbers')} 枚举投资机会…", flush=True)
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
        UserHandlers._print_simulate_version(result, "enumerate")

        # 终局摘要统一走 Strategy.present_report
        if enum_result.get("output_dir"):
            try:
                from pathlib import Path

                from core.modules.strategy import Strategy
                from core.modules.strategy.contracts import SimulateKind

                Strategy.present_report(
                    SimulateKind.ENUMERATE, Path(enum_result["output_dir"])
                )
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

        UserHandlers._print_analysis_from_step(enum_result)

    @staticmethod
    def _run_strategy_price_factor(args: argparse.Namespace) -> None:
        import time
        from pathlib import Path

        from core.modules.strategy import Strategy

        strategy_key = UserHandlers._resolve_strategy_key(getattr(args, "strategy", None))
        force = bool(getattr(args, "force", False))

        print(f"{i('market')} 价格因子回测…", flush=True)
        print(f"  策略: {strategy_key}", flush=True)
        if force:
            print("  --force: 忽略缓存，同指纹仍写入原 version", flush=True)
        print("  依赖: 同指纹枚举产物；缺失时会先补跑枚举", flush=True)

        t0 = time.perf_counter()
        result = Strategy.price_factor(
            strategy_key,
            ignore_cache=force,
        )
        wall_sec = time.perf_counter() - t0

        pf = result.get("price_factor") if isinstance(result.get("price_factor"), dict) else result
        enum_part = result.get("enumerate") if isinstance(result.get("enumerate"), dict) else None
        UserHandlers._print_simulate_version(result, "price_factor")
        if enum_part:
            print(
                f"  枚举: success={enum_part.get('success')} version={enum_part.get('version_id')}",
                flush=True,
            )

        # 终局摘要统一走 Strategy.present_report
        if isinstance(pf, dict) and pf.get("output_dir"):
            try:
                from core.modules.strategy.contracts import SimulateKind

                Strategy.present_report(SimulateKind.PRICE_FACTOR, Path(pf["output_dir"]))
            except FileNotFoundError as exc:
                logger.warning("展示价格回测汇总失败（缺产物）: %s", exc)
                print(f"  success: {pf.get('success')}", flush=True)
                print(f"  output_dir: {pf.get('output_dir')}", flush=True)
            except Exception as exc:
                logger.warning("展示价格回测汇总失败: %s", exc)
                print(f"  success: {pf.get('success')}", flush=True)
                print(f"  output_dir: {pf.get('output_dir')}", flush=True)
        else:
            print(f"  success: {pf.get('success') if isinstance(pf, dict) else False}", flush=True)

        print(f"  总耗时: {wall_sec:.2f}s", flush=True)
        if not (pf.get("success", True) if isinstance(pf, dict) else True):
            raise SystemExit(1)

        UserHandlers._print_analysis_from_step(pf if isinstance(pf, dict) else {})

    @staticmethod
    def _run_strategy_portfolio(args: argparse.Namespace) -> None:
        import time
        from pathlib import Path

        from core.modules.strategy import Strategy

        strategy_key = UserHandlers._resolve_strategy_key(getattr(args, "strategy", None))
        force = bool(getattr(args, "force", False))

        print(f"{i('money')} 组合回测（portfolio）…", flush=True)
        print(f"  策略: {strategy_key}", flush=True)
        if force:
            print("  --force: 忽略缓存，同指纹仍写入原 version", flush=True)
        print("  依赖: 同指纹枚举产物；缺失时会先补跑枚举", flush=True)

        t0 = time.perf_counter()
        result = Strategy.portfolio(
            strategy_key,
            ignore_cache=force,
        )
        wall_sec = time.perf_counter() - t0

        pf = result.get("portfolio") if isinstance(result.get("portfolio"), dict) else result
        enum_part = result.get("enumerate") if isinstance(result.get("enumerate"), dict) else None
        UserHandlers._print_simulate_version(result, "portfolio")
        if enum_part:
            print(
                f"  枚举: success={enum_part.get('success')} version={enum_part.get('version_id')}",
                flush=True,
            )

        # 终局摘要统一走 Strategy.present_report
        if isinstance(pf, dict) and pf.get("output_dir"):
            try:
                from core.modules.strategy.contracts import SimulateKind

                Strategy.present_report(SimulateKind.PORTFOLIO, Path(pf["output_dir"]))
            except FileNotFoundError as exc:
                logger.warning("展示组合回测汇总失败（缺产物）: %s", exc)
                print(f"  success: {pf.get('success')}", flush=True)
                print(f"  output_dir: {pf.get('output_dir')}", flush=True)
            except Exception as exc:
                logger.warning("展示组合回测汇总失败: %s", exc)
                print(f"  success: {pf.get('success')}", flush=True)
                print(f"  output_dir: {pf.get('output_dir')}", flush=True)
        else:
            print(f"  success: {pf.get('success') if isinstance(pf, dict) else False}", flush=True)

        print(f"  总耗时: {wall_sec:.2f}s", flush=True)
        if not (pf.get("success", True) if isinstance(pf, dict) else True):
            raise SystemExit(1)

        UserHandlers._print_analysis_from_step(pf if isinstance(pf, dict) else {})

    @staticmethod
    def _run_strategy_scan(args: argparse.Namespace) -> None:
        from core.modules.strategy import Strategy

        name = UserHandlers._strategy_name(getattr(args, "strategy", None))
        demo = bool(getattr(args, "demo", False))

        print(f"{i('search')} 扫描投资机会…", flush=True)
        if name:
            print(f"  策略: {name}", flush=True)
        else:
            print("  策略: （全部已启用）", flush=True)
        if demo:
            print("  --demo: 放宽严格交易日门闸", flush=True)

        results = Strategy.scan(name, demo=demo)
        if not results:
            print("  无扫描结果（策略被跳过或未发现）", flush=True)
            return

        for key, report in results.items():
            if not isinstance(report, dict):
                print(f"  [{key}] {report}", flush=True)
                continue
            summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
            date_meta = report.get("date_meta") if isinstance(report.get("date_meta"), dict) else {}
            print(
                f"  [{key}] date={report.get('date')} "
                f"opportunities={report.get('total_opportunities', 0)} "
                f"universe={report.get('total_stocks', 0)} "
                f"hit_stocks={summary.get('total_stocks', 0)} "
                f"at_limit_up={summary.get('at_limit_up_count', 0)}",
                flush=True,
            )
            mode_label = str(date_meta.get("mode_label") or "").strip()
            detail = str(date_meta.get("source_detail") or "").strip()
            if mode_label or detail:
                print(
                    f"         日期模式={mode_label or '?'}；{detail or '来源未记录'}",
                    flush=True,
                )

    @staticmethod
    def _run_strategy_simulate(args: argparse.Namespace) -> None:
        """完整模拟链路：price_factor → portfolio（缺失枚举时各自会先补跑）。"""
        import time

        from core.modules.strategy import Strategy

        strategy_key = UserHandlers._resolve_strategy_key(getattr(args, "strategy", None))
        force = bool(getattr(args, "force", False))

        print(f"{i('game')} 模拟链路 · PriceFactor → Portfolio …", flush=True)
        print(f"  策略: {strategy_key}", flush=True)
        if force:
            print("  --force: 忽略缓存，同指纹仍写入原 version", flush=True)

        t0 = time.perf_counter()
        pf_result = Strategy.price_factor(strategy_key, ignore_cache=force)
        pf = (
            pf_result.get("price_factor")
            if isinstance(pf_result.get("price_factor"), dict)
            else pf_result
        )
        if not (pf.get("success", True) if isinstance(pf, dict) else True):
            print(f"  price_factor 失败: {pf}", flush=True)
            raise SystemExit(1)
        print(
            f"  price_factor: success={pf.get('success') if isinstance(pf, dict) else True} "
            f"version={pf.get('version_id') if isinstance(pf, dict) else None}",
            flush=True,
        )

        po_result = Strategy.portfolio(strategy_key, ignore_cache=force)
        po = (
            po_result.get("portfolio")
            if isinstance(po_result.get("portfolio"), dict)
            else po_result
        )
        wall_sec = time.perf_counter() - t0
        if isinstance(po, dict) and po.get("output_dir"):
            try:
                from pathlib import Path

                from core.modules.strategy.contracts import SimulateKind

                Strategy.present_report(SimulateKind.PORTFOLIO, Path(po["output_dir"]))
            except Exception as exc:
                logger.warning("展示组合回测汇总失败: %s", exc)
                print(f"  portfolio success: {po.get('success')}", flush=True)
        else:
            print(
                f"  portfolio success: {po.get('success') if isinstance(po, dict) else False}",
                flush=True,
            )

        print(f"  总耗时: {wall_sec:.2f}s", flush=True)
        if not (po.get("success", True) if isinstance(po, dict) else True):
            raise SystemExit(1)

        UserHandlers._print_analysis_from_step(pf if isinstance(pf, dict) else {})
        UserHandlers._print_analysis_from_step(po if isinstance(po, dict) else {})

    @staticmethod
    def _run_strategy_analyze(args: argparse.Namespace) -> None:
        from pathlib import Path

        from core.modules.strategy import Strategy

        output_dir = getattr(args, "output_dir", None)
        if output_dir:
            Strategy.present_analysis_report(Path(output_dir))
            return

        strategy_key = UserHandlers._resolve_strategy_key(getattr(args, "strategy", None))
        step = str(getattr(args, "step", None) or "enum").strip().lower()
        version_id = getattr(args, "version", None)

        if not version_id:
            print(
                "归因已集成在 simulate 中：请在 settings.analysis.enabled=true 后运行 se/sp/so；"
                "或使用 --output-dir 展示已有 report。",
                flush=True,
            )
            raise SystemExit(1)

        for candidate in Strategy.resolve_simulation_output_dirs(
            strategy_key,
            step=step,
            slot={"version_id": str(version_id).strip()},
        ):
            if not candidate.is_dir():
                continue
            Strategy.present_analysis_report(candidate)
            return

        print(f"未找到 version {version_id!r} 的 {step} 归因报告。", flush=True)
        raise SystemExit(1)

    @staticmethod
    def _run_strategy_delete_version(args: argparse.Namespace) -> None:
        from core.modules.strategy import Strategy

        try:
            spec, sid = UserHandlers.parse_strategy_version_spec(
                getattr(args, "strategy", None)
            )
        except ValueError as exc:
            print(str(exc), flush=True)
            raise SystemExit(1) from exc

        try:
            strategy_key = Strategy.resolve(spec)
        except FileNotFoundError:
            logger.error("策略不存在: %s", spec)
            raise SystemExit(1)
        out = Strategy.delete_simulation_version(strategy_key, sid)
        if not out.get("ok"):
            print(out.get("error") or "删除失败", flush=True)
            raise SystemExit(1)
        vid_label = out.get("version_id") or f"v{sid}"
        pinned_note = "（原先已固定）" if out.get("was_pinned") else ""
        print(
            f"已删除 {strategy_key} {vid_label} 的回测产物{pinned_note}。",
            flush=True,
        )

    @staticmethod
    def _run_strategy_set_pinned(args: argparse.Namespace, pinned: bool) -> None:
        from core.modules.strategy import Strategy

        try:
            spec, sid = UserHandlers.parse_strategy_version_spec(
                getattr(args, "strategy", None)
            )
        except ValueError as exc:
            print(str(exc), flush=True)
            raise SystemExit(1) from exc

        try:
            strategy_key = Strategy.resolve(spec)
        except FileNotFoundError:
            logger.error("策略不存在: %s", spec)
            raise SystemExit(1)
        out = Strategy.set_simulation_version_pinned(strategy_key, sid, pinned)
        if not out.get("ok"):
            print(out.get("error") or "操作失败", flush=True)
            raise SystemExit(1)
        vid_label = out.get("version_id") or f"v{sid}"
        action = "已固定" if pinned else "已取消固定"
        print(f"{action} {strategy_key} {vid_label}。", flush=True)

    @staticmethod
    def _handle_strategy(cmd: str, app: CliApp, args: argparse.Namespace) -> None:
        if cmd == "strategy_enumerate":
            UserHandlers._run_strategy_enumerate(args)
            return

        if cmd == "strategy_price_factor":
            UserHandlers._run_strategy_price_factor(args)
            return

        if cmd == "strategy_portfolio":
            UserHandlers._run_strategy_portfolio(args)
            return

        if cmd == "scan":
            UserHandlers._run_strategy_scan(args)
            return

        if cmd == "strategy_simulate":
            UserHandlers._run_strategy_simulate(args)
            return

        if cmd == "strategy_analyze":
            UserHandlers._run_strategy_analyze(args)
            return

        if cmd == "strategy_delete_version":
            UserHandlers._run_strategy_delete_version(args)
            return

        if cmd == "strategy_pin_version":
            UserHandlers._run_strategy_set_pinned(args, True)
            return

        if cmd == "strategy_unpin_version":
            UserHandlers._run_strategy_set_pinned(args, False)
            return

        raise SystemExit(f"未知命令: {cmd}")

