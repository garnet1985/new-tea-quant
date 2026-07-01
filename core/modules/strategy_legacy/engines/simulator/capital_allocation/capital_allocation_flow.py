#!/usr/bin/env python3
"""Capital allocation simulation flow."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

from core.modules.strategy.engines.simulator.base_flow import BaseSimulationFlow
from core.modules.strategy.engines.simulator.capital_allocation.data_classes.flow_context import (
    CapitalAllocationExecuteContext,
    CapitalAllocationPreprocessContext,
)
from core.modules.strategy.engines.shared.data_classes.market_profile_context import (
    MarketProfileContext,
)
from core.modules.strategy.engines.shared.helpers.simulation_flow import (
    prepare_simulation_settings,
    simulation_effective_snapshot,
)
from core.modules.strategy.services.cache.simulator_res_db_cache.helpers import (
    raw_settings_for_db_cache_fingerprint,
    stock_ids_for_db_cache_fingerprint,
)
from .capital_allocation_flow_impl import CapitalAllocationFlowImpl

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )
    from core.modules.strategy.execution_manager.workbench_flow_progress import (
        WorkbenchFlowProgress,
    )


class CapitalAllocationFlow(BaseSimulationFlow):
    """Three-stage capital allocation simulation flow（支持 Simulator Res DB Cache）。"""

    def __init__(self, is_verbose: bool = False, *, force_refresh: bool = False) -> None:
        self._impl = CapitalAllocationFlowImpl(is_verbose=is_verbose)
        self._force_refresh = bool(force_refresh)
        self.last_version: int = 0
        self.used_db_cache: bool = False

    def run(
        self,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"] = None,
        *,
        progress_callback: Optional[Callable[[float], None]] = None,
        workbench_progress: Optional["WorkbenchFlowProgress"] = None,
    ) -> Any:
        """
        指纹探针 → DbCache 命中则直接返回 session summary → 否则 preprocess → execute →
        postprocess → 写 ``capital_allocation`` 槽位。

        ``progress_callback``：工作台轮询用；传入 0～100 的磁盘进度百分比（完成前宜小于 100）。
        """
        from core.modules.data_manager import DataManager
        from core.modules.strategy.engines.shared.helpers.backtest_date_resolve import (
            resolve_latest_completed_trading_date,
        )
        from core.modules.strategy.engines.simulator.price_factor.price_factor_flow_impl import (
            PriceFactorFlowImpl,
        )
        from core.modules.strategy.services.cache.simulator_res_db_cache.snapshot_slot_adapters import (
            lookup_capital_allocation_cache,
            persist_capital_allocation_snapshot,
        )
        from core.modules.strategy.services.cache.simulator_res_db_cache.finger_print.finger_print import (
            resolve_db_cache_fingerprints,
        )

        self.last_version = 0
        self.used_db_cache = False

        def tick(pct: float) -> None:
            if progress_callback is not None:
                progress_callback(float(pct))

        wp = workbench_progress
        if wp is not None:
            wp.stage("load", 0.05)
        tick(8.0)
        base_settings = self._impl.load_settings(strategy_name, strategy_info)
        config = self._impl.parse_config(base_settings)
        base_output_version_dir = self._impl.resolve_source_version(
            strategy_name=strategy_name,
            base_settings=base_settings,
            config=config,
            strategy_info=strategy_info,
        )

        scan = PriceFactorFlowImpl(is_verbose=False).scan_stock_files(base_output_version_dir)
        stock_list = stock_ids_for_db_cache_fingerprint(
            base_output_version_dir,
            fallback_ids=sorted(scan.keys()),
        )
        # 磁盘上的 settings（从磁盘上重新读取，而不是从 strategy_info 中读取）
        from core.modules.strategy.engines.shared.helpers.strategy_runtime import (
            load_strategy_info,
        )
        disk_strategy_info = load_strategy_info(strategy_name)
        disk_settings = dict(disk_strategy_info.settings.to_dict()) if disk_strategy_info else {}
        # 用户修改过的 settings（从 base_settings.to_dict() 读取）
        user_modified_settings = dict(base_settings.to_dict())

        data_mgr = DataManager(is_verbose=False)
        latest_completed_trading_date = resolve_latest_completed_trading_date(data_mgr)

        resolved = resolve_db_cache_fingerprints(
            strategy_name=str(strategy_name),
            disk_settings=disk_settings,  # 磁盘上的 settings
            user_modified_settings=user_modified_settings,  # 用户修改过的 settings
            stock_list=list(stock_list),
            latest_completed_trading_date=latest_completed_trading_date,
        )

        if wp is not None:
            wp.stage("load", 0.85)
        tick(10.0)

        if resolved is not None and not self._force_refresh:
            hit = lookup_capital_allocation_cache(
                strategy_name,
                resolved.settings_fp,
                resolved.env_fp,
                disk_settings_hash=resolved.disk_settings_hash,
            )
            if hit:
                summary, wb_version = hit
                self.used_db_cache = True
                cdir = ""
                if isinstance(summary, dict) and summary and resolved is not None:
                    cdir = str(summary.get("capital_output_version_dir") or "").strip()
                    sid = persist_capital_allocation_snapshot(
                        strategy_name,
                        settings_snapshot_api=dict(
                            resolved.normalized_settings_dict or {}
                        ),
                        report_capital_allocation=summary,
                        settings_fingerprint_id=resolved.settings_fp,
                        env_fingerprint_id=resolved.env_fp,
                        capital_output_version_dir=cdir or None,
                        disk_settings_hash=resolved.disk_settings_hash,
                    )
                    self.last_version = int(sid or wb_version or 0)
                else:
                    self.last_version = int(wb_version or 0)
                from core.modules.strategy.services.data.output.simulation_output_retention import (
                    prune_disk_output_after_sim_run,
                )

                prune_disk_output_after_sim_run(
                    strategy_name,
                    "capital",
                    base_settings.to_dict(),
                    protect_output_version_dir=cdir or None,
                )
                if wp is not None:
                    wp.stage("report", 1.0)
                tick(92.0)
                return summary

        if wp is not None:
            wp.stage("load", 1.0)
            wp.stage("dispatch", 0.1)
        tick(12.0)
        preprocessed = self.preprocess(
            strategy_name=strategy_name,
            strategy_info=strategy_info,
        )
        if wp is not None:
            wp.stage("dispatch", 1.0)
        tick(14.0)
        executed = self.execute(preprocessed, progress_callback=tick)
        if wp is not None:
            wp.stage("execute", 1.0)
        tick(90.0)
        summary = self.postprocess(preprocessed, executed, prune_disk=False)
        if wp is not None:
            wp.stage("report", 0.5)
        tick(94.0)

        if summary and isinstance(summary, dict):
            # 磁盘上的 settings（从磁盘上重新读取，而不是从 strategy_info 中读取）
            from core.modules.strategy.engines.shared.helpers.strategy_runtime import (
                load_strategy_info,
            )
            disk_strategy_info_save = load_strategy_info(strategy_name)
            disk_settings_save = dict(disk_strategy_info_save.settings.to_dict()) if disk_strategy_info_save else {}
            # 用户修改过的 settings（从 base_settings.to_dict() 读取）
            user_modified_settings_save = dict(base_settings.to_dict())
            resolved_save = resolve_db_cache_fingerprints(
                strategy_name=str(strategy_name),
                disk_settings=disk_settings_save,  # 磁盘上的 settings
                user_modified_settings=user_modified_settings_save,  # 用户修改过的 settings
                stock_list=list(stock_list),
                latest_completed_trading_date=latest_completed_trading_date,
            )
            if resolved_save is not None:
                sid = persist_capital_allocation_snapshot(
                    strategy_name,
                    settings_snapshot_api=dict(resolved_save.settings_diff or {}),  # 差异字段
                    report_capital_allocation=summary,
                    settings_fingerprint_id=resolved_save.settings_fp,
                    env_fingerprint_id=resolved_save.env_fp,
                    capital_output_version_dir=preprocessed.output_version_dir.name,
                    disk_settings_hash=resolved_save.disk_settings_hash,
                )
                self.last_version = int(sid or 0)

        from core.modules.strategy.services.data.output.simulation_output_retention import (
            prune_disk_output_after_sim_run,
        )

        prune_disk_output_after_sim_run(
            preprocessed.strategy_name,
            "capital",
            preprocessed.base_settings.to_dict(),
            protect_output_version_dir=preprocessed.output_version_dir.name,
        )

        return summary

    def preprocess(
        self,
        *,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"],
    ) -> CapitalAllocationPreprocessContext:
        # step1: read raw strategy settings
        base_settings = self._impl.load_settings(strategy_name, strategy_info)
        simulation_settings = prepare_simulation_settings(base_settings)
        # step2: parse simulator-specific config from settings
        config = self._impl.parse_config(base_settings)
        # step3: resolve source data version and create simulation version
        base_output_version_dir = self._impl.resolve_source_version(
            strategy_name=strategy_name,
            base_settings=base_settings,
            config=config,
            strategy_info=strategy_info,
        )
        output_version_dir, output_version_id = self._impl.create_output_version(
            strategy_name
        )
        # step4: initialize runtime profiling context
        profiler = self._impl.create_profiler()
        market_profile = MarketProfileContext.from_settings_view(base_settings)
        from core.modules.data_manager import DataManager
        from core.modules.strategy.engines.shared.helpers.backtest_calendar_context import (
            build_backtest_calendar_context,
        )
        from core.modules.strategy.engines.shared.helpers.backtest_date_resolve import (
            resolve_backtest_date_range,
            resolve_latest_completed_trading_date,
        )
        from core.modules.strategy.services.data.output import EnumeratorOutputWriterService

        data_mgr = DataManager(is_verbose=False)
        scope_ids = EnumeratorOutputWriterService.read_scope_stock_ids(base_output_version_dir)
        period = resolve_backtest_date_range(
            settings_view=base_settings,
            stock_ids=scope_ids,
            latest_completed_trading_date=resolve_latest_completed_trading_date(data_mgr),
            data_manager=data_mgr,
        )
        calendar_dict = build_backtest_calendar_context(
            data_manager=data_mgr,
            period=period,
            market_profile_id=market_profile.profile_id,
        ).to_dict()
        return CapitalAllocationPreprocessContext(
            strategy_name=strategy_name,
            base_settings=base_settings,
            market_profile=market_profile,
            simulation_settings=simulation_settings,
            config=config,
            base_output_version_dir=base_output_version_dir,
            output_version_dir=output_version_dir,
            output_version_id=output_version_id,
            profiler=profiler,
            backtest_calendar=calendar_dict,
        )

    def execute(
        self,
        preprocessed: CapitalAllocationPreprocessContext,
        *,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> CapitalAllocationExecuteContext:
        # step1: load ordered event stream from output artifacts
        events = self._impl.load_event_stream(
            strategy_name=preprocessed.strategy_name,
            base_output_version_dir=preprocessed.base_output_version_dir,
            config=preprocessed.config,
            base_settings=preprocessed.base_settings,
            profiler=preprocessed.profiler,
        )
        if progress_callback is not None:
            progress_callback(18.0)
        if not events:
            if progress_callback is not None:
                progress_callback(88.0)
            return CapitalAllocationExecuteContext(empty=True)
        # step2: initialize account/funding/allocation execution state
        state = self._impl.create_execution_state(
            preprocessed.config,
            market_profile=preprocessed.market_profile,
            simulation_settings=preprocessed.simulation_settings,
            backtest_calendar=preprocessed.backtest_calendar,
        )
        # step3: replay trigger/target events into trades and positions
        self._impl.replay_events(
            events=events,
            config=preprocessed.config,
            state=state,
            profiler=preprocessed.profiler,
            progress_callback=progress_callback,
        )
        # step4: flush final day equity snapshot
        self._impl.finalize_equity_curve(config=preprocessed.config, state=state)
        if progress_callback is not None:
            progress_callback(89.0)
        return CapitalAllocationExecuteContext(
            empty=False,
            events=events,
            account=state["account"],
            trades=state["trades"],
            equity_curve=state["equity_curve"],
            completed_opportunities_map=state["completed_opportunities_map"],
            tradability_skips=dict(state.get("tradability_skips") or {}),
        )

    def postprocess(
        self,
        preprocessed: CapitalAllocationPreprocessContext,
        executed: CapitalAllocationExecuteContext,
        *,
        prune_disk: bool = True,
    ) -> Dict[str, object]:
        if executed.empty:
            return {}
        # step1: aggregate execution data into strategy-level summary
        summary = self._impl.build_summary(
            account=executed.account,
            trades=executed.trades or [],
            equity_curve=executed.equity_curve or [],
            initial_capital=preprocessed.config.initial_capital,
            events=executed.events or [],
            completed_opportunities_map=executed.completed_opportunities_map or {},
            tradability_skips=executed.tradability_skips,
        )
        from core.modules.data_manager import DataManager
        from core.modules.strategy.engines.shared.helpers.backtest_date_resolve import (
            resolve_backtest_period_payload,
            resolve_latest_completed_trading_date,
        )
        from core.modules.strategy.services.data.output.enumerator_output_service import (
            EnumeratorOutputWriterService,
        )

        stock_ids = EnumeratorOutputWriterService.read_scope_stock_ids(
            preprocessed.base_output_version_dir
        )
        data_mgr = DataManager(is_verbose=False)
        summary["backtest_period"] = resolve_backtest_period_payload(
            settings_view=preprocessed.base_settings,
            stock_ids=stock_ids,
            data_manager=data_mgr,
            latest_completed_trading_date=resolve_latest_completed_trading_date(data_mgr),
        )
        # step2: persist output artifacts and metadata
        preprocessed.profiler.start_timer("save_csv")
        settings_snapshot = preprocessed.base_settings.to_dict()
        self._impl.save_outputs(
            output_version_dir=preprocessed.output_version_dir,
            output_version_id=preprocessed.output_version_id,
            base_output_version_dir=preprocessed.base_output_version_dir,
            trades=executed.trades or [],
            equity_curve=executed.equity_curve or [],
            summary=summary,
            config=preprocessed.config,
            settings_snapshot=settings_snapshot,
            simulation_effective=simulation_effective_snapshot(
                preprocessed.simulation_settings
            ),
        )
        preprocessed.profiler.metrics.time_save_csv = preprocessed.profiler.end_timer(
            "save_csv"
        )
        preprocessed.profiler.metrics.time_total = preprocessed.profiler.end_timer(
            "total"
        )
        # step3: persist performance report
        self._impl.save_performance_report(
            output_version_dir=preprocessed.output_version_dir,
            profiler=preprocessed.profiler,
        )
        # step4: trigger analyzer hooks
        self._impl.run_analyzer_hook(
            strategy_name=preprocessed.strategy_name,
            output_version_dir=preprocessed.output_version_dir,
            raw_settings=preprocessed.base_settings.to_dict(),
        )
        if prune_disk:
            from core.modules.strategy.services.data.output.simulation_output_retention import (
                prune_disk_output_after_sim_run,
            )

            prune_disk_output_after_sim_run(
                preprocessed.strategy_name,
                "capital",
                preprocessed.base_settings.to_dict(),
                protect_output_version_dir=preprocessed.output_version_dir.name,
            )
        return summary


__all__ = ["CapitalAllocationFlow"]
