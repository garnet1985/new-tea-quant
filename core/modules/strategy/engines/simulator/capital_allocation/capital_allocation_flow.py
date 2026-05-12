#!/usr/bin/env python3
"""Capital allocation simulation flow."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

from core.modules.strategy.engines.simulator.base_flow import BaseSimulationFlow
from core.modules.strategy.engines.simulator.capital_allocation.data_classes.flow_context import (
    CapitalAllocationExecuteContext,
    CapitalAllocationPreprocessContext,
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


class CapitalAllocationFlow(BaseSimulationFlow):
    """Three-stage capital allocation simulation flow（支持 Simulator Res DB Cache）。"""

    def __init__(self, is_verbose: bool = False, *, force_refresh: bool = False) -> None:
        self._impl = CapitalAllocationFlowImpl(is_verbose=is_verbose)
        self._force_refresh = bool(force_refresh)
        self.last_snapshot_id: int = 0
        self.last_run_used_db_cache: bool = False

    def run(
        self,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"] = None,
        *,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Any:
        """
        指纹探针 → DbCache 命中则直接返回 session summary → 否则 preprocess → execute →
        postprocess → 写 ``capital_allocation`` 槽位。

        ``progress_callback``：工作台轮询用；传入 0～100 的磁盘进度百分比（完成前宜小于 100）。
        """
        from core.modules.data_manager import DataManager
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

        self.last_snapshot_id = 0
        self.last_run_used_db_cache = False

        def tick(pct: float) -> None:
            if progress_callback is not None:
                progress_callback(float(pct))

        tick(8.0)

        base_settings = self._impl.load_settings(strategy_name, strategy_info)
        config = self._impl.parse_config(base_settings)
        output_version_dir = self._impl.resolve_source_version(
            strategy_name=strategy_name,
            base_settings=base_settings,
            config=config,
            strategy_info=strategy_info,
        )

        scan = PriceFactorFlowImpl(is_verbose=False).scan_stock_files(output_version_dir)
        stock_list = stock_ids_for_db_cache_fingerprint(
            output_version_dir,
            fallback_ids=sorted(scan.keys()),
        )
        raw_for_fp = raw_settings_for_db_cache_fingerprint(base_settings, strategy_info)

        data_mgr = DataManager(is_verbose=False)
        latest_completed_trading_date = str(
            data_mgr.stock.kline.load_latest_date("daily")
            or data_mgr.service.calendar.get_latest_completed_trading_date()
            or ""
        ).strip()

        resolved = resolve_db_cache_fingerprints(
            strategy_name=str(strategy_name),
            raw_settings=raw_for_fp,
            stock_list=list(stock_list),
            latest_completed_trading_date=latest_completed_trading_date,
        )

        tick(10.0)

        if resolved is not None and not self._force_refresh:
            hit = lookup_capital_allocation_cache(
                strategy_name,
                resolved.settings_fp,
                resolved.env_fp,
            )
            if hit:
                summary, snapshot_id = hit
                self.last_snapshot_id = int(snapshot_id or 0)
                self.last_run_used_db_cache = True
                tick(92.0)
                return summary

        tick(12.0)

        sim_version_dir, sim_version_id = self._impl.create_simulation_version(strategy_name)
        profiler = self._impl.create_profiler()
        preprocessed = CapitalAllocationPreprocessContext(
            strategy_name=strategy_name,
            base_settings=base_settings,
            config=config,
            output_version_dir=output_version_dir,
            sim_version_dir=sim_version_dir,
            sim_version_id=sim_version_id,
            profiler=profiler,
        )
        tick(14.0)
        executed = self.execute(preprocessed, progress_callback=tick)
        tick(90.0)
        summary = self.postprocess(preprocessed, executed)
        tick(94.0)

        if summary and isinstance(summary, dict):
            raw_save = raw_settings_for_db_cache_fingerprint(base_settings, strategy_info)
            resolved_save = resolve_db_cache_fingerprints(
                strategy_name=str(strategy_name),
                raw_settings=raw_save,
                stock_list=list(stock_list),
                latest_completed_trading_date=latest_completed_trading_date,
            )
            if resolved_save is not None:
                sid = persist_capital_allocation_snapshot(
                    strategy_name,
                    settings_snapshot_api=dict(resolved_save.normalized_settings_dict or {}),
                    report_capital_allocation=summary,
                    settings_fingerprint_id=resolved_save.settings_fp,
                    env_fingerprint_id=resolved_save.env_fp,
                    capital_sim_version_dir=preprocessed.sim_version_dir.name,
                )
                self.last_snapshot_id = int(sid or 0)

        return summary

    def preprocess(
        self,
        *,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"],
    ) -> CapitalAllocationPreprocessContext:
        # step1: read raw strategy settings
        base_settings = self._impl.load_settings(strategy_name, strategy_info)
        # step2: parse simulator-specific config from settings
        config = self._impl.parse_config(base_settings)
        # step3: resolve source data version and create simulation version
        output_version_dir = self._impl.resolve_source_version(
            strategy_name=strategy_name,
            base_settings=base_settings,
            config=config,
            strategy_info=strategy_info,
        )
        sim_version_dir, sim_version_id = self._impl.create_simulation_version(
            strategy_name
        )
        # step4: initialize runtime profiling context
        profiler = self._impl.create_profiler()
        return CapitalAllocationPreprocessContext(
            strategy_name=strategy_name,
            base_settings=base_settings,
            config=config,
            output_version_dir=output_version_dir,
            sim_version_dir=sim_version_dir,
            sim_version_id=sim_version_id,
            profiler=profiler,
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
            output_version_dir=preprocessed.output_version_dir,
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
        state = self._impl.create_execution_state(preprocessed.config)
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
        )

    def postprocess(
        self,
        preprocessed: CapitalAllocationPreprocessContext,
        executed: CapitalAllocationExecuteContext,
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
        )
        # step2: persist output artifacts and metadata
        preprocessed.profiler.start_timer("save_csv")
        self._impl.save_outputs(
            sim_version_dir=preprocessed.sim_version_dir,
            sim_version_id=preprocessed.sim_version_id,
            output_version=preprocessed.output_version_dir.name,
            trades=executed.trades or [],
            equity_curve=executed.equity_curve or [],
            summary=summary,
            config=preprocessed.config,
            settings_snapshot=preprocessed.base_settings.to_dict(),
        )
        preprocessed.profiler.metrics.time_save_csv = preprocessed.profiler.end_timer(
            "save_csv"
        )
        preprocessed.profiler.metrics.time_total = preprocessed.profiler.end_timer(
            "total"
        )
        # step3: persist performance report
        self._impl.save_performance_report(
            sim_version_dir=preprocessed.sim_version_dir,
            profiler=preprocessed.profiler,
        )
        # step4: trigger analyzer hooks
        self._impl.run_analyzer_hook(
            strategy_name=preprocessed.strategy_name,
            sim_version_dir=preprocessed.sim_version_dir,
            raw_settings=preprocessed.base_settings.to_dict(),
        )
        return summary


__all__ = ["CapitalAllocationFlow"]
