"""Dispatch parsed CLI commands to domain services."""

from __future__ import annotations
from core.infra.cmd_layout import i

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from core.modules.cli.shared.env import CliEnv
from core.modules.cli.user.app import CliApp
from core.system import system_meta

logger = logging.getLogger(__name__)


class UserHandlers:
    """User CLI command dispatch."""

    @staticmethod
    def setup_logging(verbose: bool = False) -> None:
        from core.modules.cli.shared.logging_setup import setup_cli_logging

        setup_cli_logging(verbose=verbose)

    @staticmethod
    def _strategy_name(raw: object) -> Optional[str]:
        if raw is None:
            return None
        text = str(raw).strip()
        return text or None

    @staticmethod
    def parse_strategy_version_spec(raw: object) -> tuple[str, int]:
        """``rsi_v1:3`` / ``demo/foo:v3`` → (策略, version int)。按最后一个冒号切开。"""
        from core.modules.strategy import Strategy

        return Strategy.parse_version_spec(raw)

    @staticmethod
    def run_app_update() -> int:
        from core.infra.project_context import ProjectContext

        repo_root = ProjectContext.path.get_project_root()
        updater_dir = ProjectContext.path.get_updater_directory()
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
            try:
                from core.modules.ntq_external.setup_bridge import (
                    wire_setup_package_fetcher,
                )

                wire_setup_package_fetcher()
            except ImportError:
                pass
            force = bool(getattr(args, "force", False))
            suffix = " [force]" if force else ""
            print(f"{i('ongoing')} 导入演示数据包{suffix}", flush=True)
            return Setup.runtime.import_data_pack(pack_kind="demo", force=force)

        if cmd == "auth":
            return UserHandlers.run_auth(args)

        return None

    @staticmethod
    def _auth_guide() -> str:
        return "\n".join(
            [
                "Guide：",
                "  1. 登录官网会员中心，复制通用凭证（ntq_ 开头 + 48 位小写十六进制）",
                "  2. 再执行：python cli.py auth",
                "  3. 在提示处粘贴凭证后回车（输入不回显，属正常）",
                "  4. 也可在应用设置页粘贴保存；清除用：python cli.py auth --clear",
                "  5. 仅查看是否已配置：python cli.py auth --status",
            ]
        )

    @staticmethod
    def _auth_print_status() -> int:
        from core.infra.membership import Membership

        status = Membership.status()
        if status["configured"]:
            print(f"{i('success')} 已配置会员凭证（{status['path']}）", flush=True)
            return 0
        if status["invalid"]:
            print(
                f"{i('error')} 凭证文件存在但格式无效（{status['path']}）",
                flush=True,
            )
            print(UserHandlers._auth_guide(), flush=True)
            return 1
        print(f"{i('warning')} 尚未配置会员凭证", flush=True)
        print(UserHandlers._auth_guide(), flush=True)
        return 1

    @staticmethod
    def run_auth(args: argparse.Namespace) -> int:
        """Prompt for membership token via getpass; never echo or print the secret."""
        import getpass

        from core.infra.membership import Membership

        clear = bool(getattr(args, "clear", False))
        status_only = bool(getattr(args, "status", False))

        if clear and status_only:
            print(
                f"{i('error')} 请二选一：cli.py auth / auth --status / auth --clear",
                flush=True,
            )
            return 1

        if clear:
            Membership.clear()
            print(f"{i('success')} 已清除本地会员凭证", flush=True)
            return 0

        if status_only:
            return UserHandlers._auth_print_status()

        try:
            token_text = getpass.getpass("会员凭证（输入不回显）: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(flush=True)
            print(f"{i('error')} 设置失败", flush=True)
            print(UserHandlers._auth_guide(), flush=True)
            return 1

        if not token_text:
            print(f"{i('error')} 设置失败（未输入凭证）", flush=True)
            print(UserHandlers._auth_guide(), flush=True)
            return 1

        err = Membership.save(token_text)
        if err:
            print(f"{i('error')} 设置失败", flush=True)
            print(f"  {err}", flush=True)
            print(UserHandlers._auth_guide(), flush=True)
            return 1

        try:
            from core.infra.trace import Trace

            Trace.track_member_bind(source="cli_auth", force=True)
        except Exception:
            pass

        print(f"{i('success')} token 设置成功", flush=True)
        return 0

    @staticmethod
    def _run_scaffold(kind: str, raw_path: object, args: argparse.Namespace) -> int:
        path = str(raw_path or "").strip()
        if not path:
            raise SystemExit(f"new_{kind} 需要目标路径")

        UserHandlers.setup_logging(verbose=args.verbose)

        if kind == "tag":
            from core.modules.tag import Tag

            out = Tag.scaffold_from_template(path)
            label = "Tag 场景"
        else:
            from core.modules.strategy import Strategy

            out = Strategy.scaffold_from_template(path)
            label = "策略"
        if not out.get("ok"):
            print(f"{i('error')} {out.get('error') or '新建失败'}", flush=True)
            return 1
        print(f"{i('success')} 已新建 {label}: {out.get('key')}", flush=True)
        print(f"   目录: {out.get('dest') or out.get('path')}", flush=True)
        print("   请编辑 settings.py 与 worker，然后运行回测或打标。", flush=True)
        return 0

    @staticmethod
    def execute(args: argparse.Namespace, app: CliApp) -> None:
        cmd = args.command

        if cmd == "renew":
            UserHandlers._handle_renew(app, args)
            return

        if cmd == "list":
            from core.modules.cli.user.list_catalog import run as run_list_catalog

            code = run_list_catalog(
                getattr(args, "resource", None),
                as_json=bool(getattr(args, "json", False)),
            )
            if code != 0:
                raise SystemExit(code)
            return

        if cmd == "export_adj_factor":
            print(f"{i('upload')} 手动导出复权因子事件季度 CSV...", flush=True)
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
            print(f"{i('tag')}  执行标签计算...", flush=True)
            dry_run = getattr(args, "dry_run", False)
            if dry_run:
                print(f"{i('warning')}  DRY RUN 模式：计算结果不会写入数据库", flush=True)
            app.tag(
                scenario_name=getattr(args, "scenario", None),
                dry_run=dry_run,
                entity_limit=getattr(args, "entity_limit", None),
            )
            return

        if cmd == "series_relation":
            UserHandlers._run_series_relation(args)
            return

        if cmd == "agent":
            UserHandlers._run_agent(args)
            return

        if cmd in (
            "scan",
            "strategy_enumerate",
            "strategy_price_factor",
            "strategy_portfolio",
            "strategy_decision",
            "strategy_decision_list",
            "strategy_decision_delete",
            "strategy_simulate",
            "strategy_attribute_enumerate",
            "strategy_attribute_price",
            "strategy_attribute_portfolio",
            "strategy_rolling",
            "strategy_delete_version",
        ):
            UserHandlers._handle_strategy(cmd, app, args)
            return

        raise SystemExit(f"未知命令: {cmd}")

    @staticmethod
    def _handle_renew(app: CliApp, args: argparse.Namespace) -> None:
        source = UserHandlers._strategy_name(getattr(args, "source", None))
        force = bool(getattr(args, "force", False))

        if getattr(args, "clear_logs", False):
            from core.modules.data_source import DataSourceManager

            removed = DataSourceManager.clear_finished_runs()
            if not removed:
                print("没有可清理的运行状态。", flush=True)
                return
            print(f"已清理 {len(removed)} 次运行状态。", flush=True)
            return

        if source and source.lower() == "list":
            from core.modules.data_source import DataSourceManager

            if getattr(args, "json", False):
                import json

                print(
                    json.dumps(DataSourceManager().task_catalog(force=force), ensure_ascii=False),
                    flush=True,
                )
                return
            print(DataSourceManager.format_renew_targets_help(), flush=True)
            return

        if source:
            refresh = " [force refresh]" if force else ""
            print(f"{i('ongoing')} 更新数据: {source}{refresh}", flush=True)
        else:
            refresh = " [force]" if force else ""
            print(f"{i('ongoing')} 更新全部已启用数据源{refresh}", flush=True)

        try:
            asyncio.run(app.renew_data(table_name=source, force=force))
        except ValueError as exc:
            print(f"{i('error')} {exc}", flush=True)
            raise SystemExit(1) from exc

    @staticmethod
    def _resolve_strategy_key(name: Optional[str]) -> str:
        from core.modules.strategy import Strategy

        out = Strategy.resolve_default_enabled_key(
            UserHandlers._strategy_name(name) or None
        )
        if not out.get("ok"):
            msg = str(out.get("message") or "策略不可用")
            print(msg, flush=True)
            choices = out.get("choices") or []
            if choices and "未启用" in msg:
                print(f"可用 meta.key: {', '.join(sorted(choices))}", flush=True)
            raise SystemExit(1)
        note = str(out.get("message") or "").strip()
        if note:
            print(note, flush=True)
        return str(out.get("key") or "")

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

        print(f"{i('numbers')} 机会盘点…", flush=True)
        print(f"  策略: {strategy_key}", flush=True)
        if stock_count is not None:
            print(f"  采样: {stock_count} 只股票", flush=True)
        else:
            print(
                "  提示: 未传 --stocks 时将按 settings.sampling 抽样（可能数百只，耗时较长）",
                flush=True,
            )
        print(f"  {Strategy.describe_enumerate_progress_hint()}", flush=True)

        t0 = time.perf_counter()
        result = Strategy.enumerate(
            strategy_key,
            ignore_cache=force,
            runtime_settings=runtime_settings or None,
        )
        wall_sec = time.perf_counter() - t0

        enum_result = result.get("enum") if isinstance(result.get("enum"), dict) else result
        UserHandlers._print_simulate_version(result, "enum")

        # 终局摘要统一走 Strategy.present_report
        if enum_result.get("output_dir"):
            try:
                from core.modules.strategy import Strategy
                from core.modules.strategy.contracts import SimulateKind

                Strategy.present_report(
                    SimulateKind.ENUMERATE, Path(enum_result["output_dir"])
                )
            except FileNotFoundError as exc:
                print(f"  展示机会盘点汇总失败（缺产物）: {exc}", flush=True)
                print(f"  success: {enum_result.get('success')}", flush=True)
                print(f"  output_dir: {enum_result.get('output_dir')}", flush=True)
            except Exception as exc:
                print(f"  展示机会盘点汇总失败: {exc}", flush=True)
                logger.warning("展示机会盘点汇总失败", exc_info=True)
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

    @staticmethod
    def _run_strategy_price_factor(args: argparse.Namespace) -> None:
        import time

        from core.modules.strategy import Strategy

        strategy_key = UserHandlers._resolve_strategy_key(getattr(args, "strategy", None))
        force = bool(getattr(args, "force", False))

        print(f"{i('market')} 价格因子回测…", flush=True)
        print(f"  策略: {strategy_key}", flush=True)
        if force:
            print("  --force: 忽略缓存，同指纹仍写入原 version", flush=True)
        print("  依赖: 同指纹机会盘点产物；缺失时会先补跑机会盘点", flush=True)

        t0 = time.perf_counter()
        result = Strategy.price_factor(
            strategy_key,
            ignore_cache=force,
        )
        wall_sec = time.perf_counter() - t0

        pf = result.get("price") if isinstance(result.get("price"), dict) else result
        enum_part = result.get("enum") if isinstance(result.get("enum"), dict) else None
        UserHandlers._print_simulate_version(result, "price")
        if enum_part:
            print(
                f"  机会盘点: success={enum_part.get('success')} version={enum_part.get('version_id')}",
                flush=True,
            )

        # 终局摘要统一走 Strategy.present_report
        if isinstance(pf, dict) and pf.get("output_dir"):
            try:
                from core.modules.strategy.contracts import SimulateKind

                Strategy.present_report(SimulateKind.PRICE_FACTOR, Path(pf["output_dir"]))
            except FileNotFoundError as exc:
                print(f"  展示价格回测汇总失败（缺产物）: {exc}", flush=True)
                print(f"  success: {pf.get('success')}", flush=True)
                print(f"  output_dir: {pf.get('output_dir')}", flush=True)
            except Exception as exc:
                print(f"  展示价格回测汇总失败: {exc}", flush=True)
                logger.warning("展示价格回测汇总失败", exc_info=True)
                print(f"  success: {pf.get('success')}", flush=True)
                print(f"  output_dir: {pf.get('output_dir')}", flush=True)
        else:
            print(f"  success: {pf.get('success') if isinstance(pf, dict) else False}", flush=True)

        print(f"  总耗时: {wall_sec:.2f}s", flush=True)
        if not (pf.get("success", True) if isinstance(pf, dict) else True):
            raise SystemExit(1)

    @staticmethod
    def _run_strategy_portfolio(args: argparse.Namespace) -> None:
        import time

        from core.modules.strategy import Strategy

        strategy_key = UserHandlers._resolve_strategy_key(getattr(args, "strategy", None))
        force = bool(getattr(args, "force", False))

        print(f"{i('money')} 组合回测（portfolio）…", flush=True)
        print(f"  策略: {strategy_key}", flush=True)
        if force:
            print("  --force: 忽略缓存，同指纹仍写入原 version", flush=True)
        print("  依赖: 同指纹机会盘点产物；缺失时会先补跑机会盘点", flush=True)

        t0 = time.perf_counter()
        result = Strategy.portfolio(
            strategy_key,
            ignore_cache=force,
        )
        wall_sec = time.perf_counter() - t0

        pf = result.get("portfolio") if isinstance(result.get("portfolio"), dict) else result
        enum_part = result.get("enum") if isinstance(result.get("enum"), dict) else None
        UserHandlers._print_simulate_version(result, "portfolio")
        if enum_part:
            print(
                f"  机会盘点: success={enum_part.get('success')} version={enum_part.get('version_id')}",
                flush=True,
            )

        # 终局摘要统一走 Strategy.present_report
        if isinstance(pf, dict) and pf.get("output_dir"):
            try:
                from core.modules.strategy.contracts import SimulateKind

                Strategy.present_report(SimulateKind.PORTFOLIO, Path(pf["output_dir"]))
            except FileNotFoundError as exc:
                print(f"  展示组合回测汇总失败（缺产物）: {exc}", flush=True)
                print(f"  success: {pf.get('success')}", flush=True)
                print(f"  output_dir: {pf.get('output_dir')}", flush=True)
            except Exception as exc:
                print(f"  展示组合回测汇总失败: {exc}", flush=True)
                logger.warning("展示组合回测汇总失败", exc_info=True)
                print(f"  success: {pf.get('success')}", flush=True)
                print(f"  output_dir: {pf.get('output_dir')}", flush=True)
        else:
            print(f"  success: {pf.get('success') if isinstance(pf, dict) else False}", flush=True)

        print(f"  总耗时: {wall_sec:.2f}s", flush=True)
        if not (pf.get("success", True) if isinstance(pf, dict) else True):
            raise SystemExit(1)

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
        """一次跑完机会盘点、价格和资金。任一层失败即停。"""
        UserHandlers._run_strategy_enumerate(args)
        UserHandlers._run_strategy_price_factor(args)
        UserHandlers._run_strategy_portfolio(args)

    @staticmethod
    def _run_strategy_attribute(
        args: argparse.Namespace,
        *,
        layer: str,
        api_name: str,
        title: str,
        need_cli: str,
    ) -> None:
        import time

        from core.modules.strategy import Strategy

        strategy_key = UserHandlers._resolve_strategy_key(getattr(args, "strategy", None))
        force = bool(getattr(args, "force", False))

        print(f"{i('bar_chart')} {title}…", flush=True)
        print(f"  策略: {strategy_key}", flush=True)
        print(f"  层: {layer}", flush=True)
        print("  配置: attribution.py（不进指纹）", flush=True)
        print(f"  须先有主 version（先跑 `{need_cli}`）", flush=True)
        if force:
            print("  --force: 忽略缓存，同指纹仍写入原副本号", flush=True)

        t0 = time.perf_counter()
        runner = getattr(Strategy, api_name)
        try:
            result = runner(strategy_key, ignore_cache=force)
        except ValueError as exc:
            print(f"{i('error')} {exc}", flush=True)
            raise SystemExit(1) from exc
        wall_sec = time.perf_counter() - t0

        try:
            Strategy.present_campaign(result)
        except Exception as exc:
            print(f"  展示战役报告失败: {exc}", flush=True)
            logger.warning("展示战役报告失败", exc_info=True)
            print(f"  headline: {result.get('headline')}", flush=True)
            print(f"  report_path: {result.get('report_path')}", flush=True)

        print(f"  总耗时: {wall_sec:.2f}s", flush=True)
        if not result.get("success", True):
            raise SystemExit(1)

    @staticmethod
    def _run_strategy_rolling(args: argparse.Namespace) -> None:
        import time

        from core.modules.strategy import Strategy

        strategy_key = UserHandlers._resolve_strategy_key(getattr(args, "strategy", None))
        force = bool(getattr(args, "force", False))

        print(f"{i('bar_chart')} 滚动对照…", flush=True)
        print(f"  策略: {strategy_key}", flush=True)
        print("  配置: rolling.py（不进指纹）", flush=True)
        if force:
            print("  --force: 忽略缓存，重跑各窗口", flush=True)

        t0 = time.perf_counter()
        result = Strategy.rolling(strategy_key, ignore_cache=force)
        wall_sec = time.perf_counter() - t0

        try:
            Strategy.present_rolling(result)
        except Exception as exc:
            print(f"  展示滚动报告失败: {exc}", flush=True)
            logger.warning("展示滚动报告失败", exc_info=True)
            print(f"  report_path: {result.get('report_path')}", flush=True)

        print(f"  总耗时: {wall_sec:.2f}s", flush=True)
        if not result.get("success", True):
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
            print(f"策略不存在: {spec}", flush=True)
            raise SystemExit(1)
        out = Strategy.delete_simulation_version(strategy_key, sid)
        if not out.get("ok"):
            print(out.get("error") or "删除失败", flush=True)
            raise SystemExit(1)
        vid_label = out.get("version_id") or f"v{sid}"
        print(
            f"已删除 {strategy_key} {vid_label} 的回测产物。",
            flush=True,
        )

    @staticmethod
    def _run_strategy_decision(args: argparse.Namespace) -> None:
        from core.modules.strategy import Strategy

        strategy_key = UserHandlers._resolve_strategy_key(getattr(args, "strategy", None))
        try:
            code = Strategy.decision_repl(
                strategy_key,
                version_id=getattr(args, "version", None),
                session_id=getattr(args, "session_id", None),
                new_session=bool(getattr(args, "new_session", False)),
            )
        except ValueError as exc:
            UserHandlers._print_decision_error(exc)
            raise SystemExit(1) from exc
        if int(code or 0) != 0:
            raise SystemExit(int(code))

    @staticmethod
    def _run_strategy_decision_list(args: argparse.Namespace) -> None:
        from core.modules.strategy import Strategy

        strategy_key = UserHandlers._resolve_strategy_key(getattr(args, "strategy", None))
        try:
            payload = Strategy.decision_list(
                strategy_key, version_id=getattr(args, "version", None)
            )
        except ValueError as exc:
            print(str(exc), flush=True)
            raise SystemExit(1) from exc
        sessions = list(payload.get("sessions") or [])
        print(
            f"决策者 version {payload.get('version_id')}  {payload.get('strategy_key')}"
            f"{'  （已有机器 portfolio）' if payload.get('has_portfolio') else ''}",
            flush=True,
        )
        if not sessions:
            print("  （无会话）", flush=True)
            return
        for row in sessions:
            UserHandlers._print_decision_row(row)

    @staticmethod
    def _run_strategy_decision_delete(args: argparse.Namespace) -> None:
        from core.modules.strategy import Strategy

        strategy_key = UserHandlers._resolve_strategy_key(getattr(args, "strategy", None))
        try:
            out = Strategy.decision_delete(
                strategy_key,
                str(getattr(args, "session_id", "") or ""),
                version_id=getattr(args, "version", None),
            )
        except ValueError as exc:
            print(str(exc), flush=True)
            raise SystemExit(1) from exc
        print(
            f"已删除决策者会话 {out.get('dm_id')}（version {out.get('version_id')}）。",
            flush=True,
        )

    @staticmethod
    def _print_decision_error(exc: BaseException) -> None:
        print(str(exc), flush=True)
        sessions = getattr(exc, "sessions", None)
        if not sessions:
            return
        for row in sessions:
            UserHandlers._print_decision_row(row)
        print("用法: python cli.py sd --session <id>  或  --new-session", flush=True)

    @staticmethod
    def _print_decision_row(row: dict) -> None:
        dm_id = row.get("dm_id") or ""
        status = row.get("status") or ""
        label = "进行中" if status == "in_progress" else "已完成"
        raw = str(row.get("current_date") or "").strip()
        if len(raw) == 8 and raw.isdigit():
            date = f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
        else:
            date = raw or "—"
        print(f"  {dm_id}  {label}  {date}", flush=True)

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

        if cmd == "strategy_decision":
            UserHandlers._run_strategy_decision(args)
            return

        if cmd == "strategy_decision_list":
            UserHandlers._run_strategy_decision_list(args)
            return

        if cmd == "strategy_decision_delete":
            UserHandlers._run_strategy_decision_delete(args)
            return

        if cmd == "scan":
            UserHandlers._run_strategy_scan(args)
            return

        if cmd == "strategy_simulate":
            UserHandlers._run_strategy_simulate(args)
            return

        if cmd == "strategy_attribute_enumerate":
            UserHandlers._run_strategy_attribute(
                args,
                layer="enum",
                api_name="attribute_enumerate",
                title="机会盘点层归因",
                need_cli="se",
            )
            return

        if cmd == "strategy_attribute_price":
            UserHandlers._run_strategy_attribute(
                args,
                layer="price",
                api_name="attribute_price",
                title="价格层归因",
                need_cli="sp",
            )
            return

        if cmd == "strategy_attribute_portfolio":
            UserHandlers._run_strategy_attribute(
                args,
                layer="portfolio",
                api_name="attribute_portfolio",
                title="组合层归因",
                need_cli="so",
            )
            return

        if cmd == "strategy_rolling":
            UserHandlers._run_strategy_rolling(args)
            return

        if cmd == "strategy_delete_version":
            UserHandlers._run_strategy_delete_version(args)
            return

        raise SystemExit(f"未知命令: {cmd}")

    @staticmethod
    def _run_agent(args: argparse.Namespace) -> None:
        from core.modules.agent import Agent
        from core.modules.agent.contracts import AgentError

        UserHandlers.setup_logging(verbose=bool(getattr(args, "verbose", False)))
        session_id = str(getattr(args, "agent_session", None) or "").strip() or None
        provider_id = str(getattr(args, "agent_provider", None) or "").strip() or None

        try:
            if getattr(args, "agent_tools", False):
                tools = Agent.list_tools()
                if not tools:
                    print("尚未登记工具。")
                    return
                print("Agent 工具:")
                for tool in tools:
                    flag = "ok" if tool.implemented else "stub"
                    print(f"  - {tool.name} [{flag}]  {tool.description}")
                return

            if getattr(args, "agent_clear", False):
                Agent.clear_session(session_id)
                sid = session_id or "default"
                print(f"已清空会话 {sid}（偏好与策略未改）。")
                return

            if getattr(args, "agent_prefs", False):
                rules = Agent.list_preferences()
                if not rules:
                    print("还没有跨会话偏好。")
                    return
                print("跨会话偏好:")
                for rule in rules:
                    print(f"  - {rule}")
                return

            remember = getattr(args, "agent_remember", None)
            if remember is not None:
                text = str(remember or "").strip()
                if not text:
                    raise SystemExit("--remember 需要非空 RULE")
                rules = Agent.remember(text)
                print(f"已记住（共 {len(rules)} 条）。")
                return

            forget = getattr(args, "agent_forget", None)
            if forget is not None:
                text = str(forget or "").strip()
                if not text:
                    raise SystemExit("--forget 需要非空 RULE")
                rules = Agent.forget(text)
                print(f"已删除（剩余 {len(rules)} 条）。")
                return

            if getattr(args, "agent_settings", False):
                settings = Agent.get_settings()
                print(f"default_provider_id: {settings.get('default_provider_id')}")
                print(
                    f"context_prompt ({settings.get('context_prompt_max_chars')} chars max):"
                )
                prompt = str(settings.get("context_prompt") or "").strip()
                print(prompt if prompt else "  (empty)")
                prefs = settings.get("preferences") or []
                print(f"preferences ({len(prefs)}):")
                if not prefs:
                    print("  (none)")
                else:
                    for rule in prefs:
                        print(f"  - {rule}")
                return

            set_provider = getattr(args, "agent_set_provider", None)
            if set_provider is not None:
                pid = str(set_provider or "").strip()
                if not pid:
                    raise SystemExit("--set-provider 需要非空 ID")
                settings = Agent.update_settings(default_provider_id=pid)
                print(f"默认 Provider → {settings.get('default_provider_id')}")
                return

            if getattr(args, "agent_set_context", None) is not None:
                text = str(getattr(args, "agent_set_context") or "")
                settings = Agent.update_settings(context_prompt=text)
                saved = str(settings.get("context_prompt") or "").strip()
                print("补充说明已更新。" if saved else "补充说明已清空。")
                return

            message = str(getattr(args, "message", None) or "").strip()
            if not message:
                raise SystemExit(
                    "用法: cli.py a \"一句话\" | cli.py agent --tools|--clear|--prefs|"
                    "--settings|--remember RULE|--forget RULE|"
                    "--set-provider ID|--set-context TEXT"
                )

            print(f"{i('sparkle')} Agent 处理中…", flush=True)
            outcome = Agent.run(
                message, session_id=session_id, provider_id=provider_id
            )
            reply = str((outcome or {}).get("reply") or "").strip()
            mode = str((outcome or {}).get("mode") or "ask")
            spent = (outcome or {}).get("catfood_spent")
            balance = (outcome or {}).get("balance")
            print(reply or "(空回复)")
            meta = [f"mode={mode}"]
            if spent is not None:
                meta.append(f"catfood_spent={spent}")
            if balance is not None:
                meta.append(f"balance={balance}")
            print(f"[{' · '.join(meta)}]")
        except AgentError as exc:
            raise SystemExit(str(exc)) from exc
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc

    def _run_series_relation(args: argparse.Namespace) -> None:
        from core.modules.series_relation import SeriesRelation

        if getattr(args, "list", False):
            infos = SeriesRelation.list_infos()
            if not infos:
                print(
                    "未发现 series_relation"
                    "（检查 userspace/extensions/series_relation/*/settings.py）"
                )
                raise SystemExit(1)
            print("可用 series_relation:")
            for info in infos:
                print(f"  - {info.key:<24} id={info.relative_path}  {info.display_name}")
            return

        key = UserHandlers._strategy_name(getattr(args, "key", None))
        if not key:
            raise SystemExit(
                "用法: cli.py srel KEY | cli.py series_relation --list"
            )
        print(f"{i('bar_chart')} 序列关系: {key}", flush=True)
        result = SeriesRelation.run(key)
        if not result.get("success"):
            raise SystemExit(result.get("error") or "series_relation 失败")
        report = str(result.get("report") or "").strip()
        if report:
            print(flush=True)
            print(report, end="" if report.endswith("\n") else "\n", flush=True)
        print(
            f"产物: {result.get('output_dir')}  "
            f"(series.json / summary.json / findings.md / report.txt)",
            flush=True,
        )

