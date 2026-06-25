#!/usr/bin/env python3
"""Price factor simulation flow."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, NamedTuple, Optional

from core.modules.strategy.engines.simulator.base_flow import BaseSimulationFlow
from core.modules.strategy.services.cache.simulator_res_db_cache.helpers import (
    raw_settings_for_db_cache_fingerprint,
    stock_ids_for_db_cache_fingerprint,
)
from core.modules.strategy.engines.shared.data_classes.market_profile_context import (
    MarketProfileContext,
)
from core.modules.strategy.engines.shared.helpers.simulation_flow import (
    prepare_simulation_settings,
    simulation_effective_snapshot,
)
from core.modules.strategy.engines.simulator.price_factor.data_classes.flow_context import (
    PriceFactorExecuteContext,
    PriceFactorPreprocessContext,
)
from .price_factor_flow_impl import PriceFactorFlowImpl

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )
    from core.modules.strategy.execution_manager.workbench_flow_progress import (
        WorkbenchFlowProgress,
    )
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
        StrategySettingsView,
    )


class _PriceFactorProbe(NamedTuple):
    """枚举输出解析完成后、尚未创建本次 price_factor 版本目录前的中间状态。"""

    strategy_name: str
    base_settings: "StrategySettingsView"
    simulator_config: Any
    base_output_version_dir: Path
    output_root: Path
    stock_files: Dict[str, Dict[str, Path]]


class PriceFactorFlow(BaseSimulationFlow):
    """Three-stage price factor simulation flow（支持 Simulator Res DB Cache）。"""

    def __init__(self, is_verbose: bool = False, *, force_refresh: bool = False) -> None:
        self._impl = PriceFactorFlowImpl(is_verbose=is_verbose)
        self._force_refresh = bool(force_refresh)
        self.last_version: int = 0
        self.used_db_cache: bool = False

    def _probe(
        self,
        *,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"],
    ) -> _PriceFactorProbe:
        base_settings = self._impl.load_settings(strategy_name, strategy_info)
        simulator_config = self._impl.parse_config(base_settings)
        base_output_version_dir, output_root = self._impl.resolve_source_version(
            strategy_name=strategy_name,
            base_settings=base_settings,
            config=simulator_config,
            strategy_info=strategy_info,
        )
        stock_files = self._impl.scan_stock_files(base_output_version_dir)
        return _PriceFactorProbe(
            strategy_name=strategy_name,
            base_settings=base_settings,
            simulator_config=simulator_config,
            base_output_version_dir=base_output_version_dir,
            output_root=output_root,
            stock_files=stock_files,
        )

    def _finish_probe(self, probe: _PriceFactorProbe) -> PriceFactorPreprocessContext:
        output_version_dir, output_version_id = self._impl.create_output_version(
            probe.strategy_name
        )
        simulation_settings = prepare_simulation_settings(probe.base_settings)
        market_profile = MarketProfileContext.from_settings_view(probe.base_settings)
        return PriceFactorPreprocessContext(
            strategy_name=probe.strategy_name,
            base_settings=probe.base_settings,
            market_profile=market_profile,
            simulation_settings=simulation_settings,
            simulator_config=probe.simulator_config,
            base_output_version_dir=probe.base_output_version_dir,
            output_root=probe.output_root,
            output_version_dir=output_version_dir,
            output_version_id=output_version_id,
            stock_files=probe.stock_files,
        )

    def run(
        self,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"] = None,
        *,
        progress_callback: Optional[Callable[[float], None]] = None,
        workbench_progress: Optional["WorkbenchFlowProgress"] = None,
    ) -> Any:
        """
        轻量 probe → 指纹解析成功则尝试 DbCache → 否则创建版本目录并
        preprocess（等价）→ execute → postprocess → 再写缓存。

        ``progress_callback``：工作台轮询用；传入 0～100 的磁盘进度百分比（完成前宜小于 100）。
        """
        from core.modules.data_manager import DataManager
        from core.modules.strategy.engines.shared.helpers.backtest_date_resolve import (
            resolve_backtest_date_range,
            resolve_latest_completed_trading_date,
        )
        from core.modules.strategy.services.cache.simulator_res_db_cache.snapshot_slot_adapters import (
            lookup_price_factor_cache,
            persist_price_factor_snapshot,
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
        probe = self._probe(strategy_name=strategy_name, strategy_info=strategy_info)
        stock_list = stock_ids_for_db_cache_fingerprint(
            probe.base_output_version_dir,
            fallback_ids=sorted(probe.stock_files.keys()),
        )
        # 磁盘上的 settings（从磁盘上重新读取，而不是从 strategy_info 中读取）
        from core.modules.strategy.engines.shared.helpers.strategy_runtime import (
            load_strategy_info,
        )
        disk_strategy_info = load_strategy_info(strategy_name)
        disk_settings = dict(disk_strategy_info.settings.to_dict()) if disk_strategy_info else {}
        # 用户修改过的 settings（从 probe.base_settings.to_dict() 读取）
        user_modified_settings = dict(probe.base_settings.to_dict())

        data_mgr = DataManager(is_verbose=False)
        latest_completed_trading_date = resolve_latest_completed_trading_date(data_mgr)

        resolved_probe = resolve_db_cache_fingerprints(
            strategy_name=str(strategy_name),
            disk_settings=disk_settings,  # 磁盘上的 settings
            user_modified_settings=user_modified_settings,  # 用户修改过的 settings
            stock_list=list(stock_list),
            latest_completed_trading_date=latest_completed_trading_date,
        )

        if wp is not None:
            wp.stage("load", 0.85)
        tick(10.0)
        if resolved_probe is not None and not self._force_refresh:
            hit = lookup_price_factor_cache(
                strategy_name,
                resolved_probe.settings_fp,
                resolved_probe.env_fp,
            )
            if hit:
                summary, wb_version = hit
                self.last_version = int(wb_version or 0)
                self.used_db_cache = True
                from core.modules.strategy.services.data.output.simulation_output_retention import (
                    prune_disk_outputs_for_strategy,
                )

                prune_disk_outputs_for_strategy(
                    strategy_name, probe.base_settings.to_dict()
                )
                if wp is not None:
                    wp.stage("report", 1.0)
                tick(92.0)
                return summary

        if wp is not None:
            wp.stage("load", 1.0)
            wp.stage("dispatch", 0.1)
        tick(12.0)
        preprocessed = self._finish_probe(probe)
        if wp is not None:
            wp.stage("dispatch", 1.0)
        tick(14.0)
        executed = self.execute(preprocessed, progress_callback=tick)
        if wp is not None:
            wp.stage("execute", 1.0)
        tick(90.0)
        summary = self.postprocess(preprocessed, executed)
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
            # 用户修改过的 settings（从 preprocessed.base_settings.to_dict() 读取）
            user_modified_settings_save = dict(preprocessed.base_settings.to_dict())

            resolved_save = resolve_db_cache_fingerprints(
                strategy_name=str(strategy_name),
                disk_settings=disk_settings_save,  # 磁盘上的 settings
                user_modified_settings=user_modified_settings_save,  # 用户修改过的 settings
                stock_list=list(stock_list),
                latest_completed_trading_date=latest_completed_trading_date,
            )
            if resolved_save is not None:
                sid = persist_price_factor_snapshot(
                    strategy_name,
                    settings_snapshot_api=dict(resolved_save.settings_diff or {}),  # 差异字段
                    report_price_factor=summary,
                    settings_fingerprint_id=resolved_save.settings_fp,
                    env_fingerprint_id=resolved_save.env_fp,
                )
                self.last_version = int(sid or 0)
        return summary

    def preprocess(
        self,
        *,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"],
    ) -> PriceFactorPreprocessContext:
        probe = self._probe(strategy_name=strategy_name, strategy_info=strategy_info)
        return self._finish_probe(probe)

    def execute(
        self,
        preprocessed: PriceFactorPreprocessContext,
        *,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> PriceFactorExecuteContext:
        from core.modules.data_manager import DataManager
        from core.modules.strategy.engines.shared.helpers.backtest_date_resolve import (
            resolve_backtest_date_range,
            resolve_latest_completed_trading_date,
        )

        jobs = self._impl.build_worker_jobs(
            strategy_name=preprocessed.strategy_name,
            output_version_dir=preprocessed.output_version_dir,
            stock_files=preprocessed.stock_files,
            config=preprocessed.simulator_config,
        )
        data_mgr = DataManager(is_verbose=False)
        period = resolve_backtest_date_range(
            settings_view=preprocessed.base_settings,
            stock_ids=sorted(preprocessed.stock_files.keys()),
            latest_completed_trading_date=resolve_latest_completed_trading_date(data_mgr),
            data_manager=data_mgr,
        )
        sim_snap = simulation_effective_snapshot(preprocessed.simulation_settings)
        mp_id = preprocessed.market_profile.profile_id
        from core.modules.strategy.engines.shared.helpers.backtest_calendar_context import (
            build_backtest_calendar_context,
        )

        calendar_dict = build_backtest_calendar_context(
            data_manager=data_mgr,
            period=period,
            market_profile_id=mp_id,
        ).to_dict()
        for job in jobs:
            job["market_profile_id"] = mp_id
            job["backtest_calendar"] = calendar_dict
            cfg = dict(job.get("config") or {})
            cfg["simulation"] = sim_snap
            cfg["start_date"] = period.start_date
            cfg["end_date"] = period.end_date
            cfg["backtest_calendar"] = calendar_dict
            cfg["goal"] = dict(preprocessed.base_settings.goal or {})
            job["config"] = cfg

        from core.infra.db.engines.duckdb.process_pool_scope import (
            duckdb_worker_pool_main_process,
        )
        from core.modules.strategy.engines.simulator.price_factor.dispatch_jobs import (
            build_price_dispatch_jobs,
        )
        from core.modules.strategy.services.execution.price_dispatch import (
            maybe_run_price_dispatch_probe,
            resolve_price_dispatch_plan,
        )

        with duckdb_worker_pool_main_process(data_mgr):
            measured = maybe_run_price_dispatch_probe(
                per_stock_jobs=jobs,
                data_mgr=data_mgr,
            )
            dispatch_plan = resolve_price_dispatch_plan(
                total_stocks=len(jobs),
                measured_timing=measured,
            )
            dispatch_jobs = build_price_dispatch_jobs(
                per_stock_jobs=jobs,
                entities_per_job=dispatch_plan.entities_per_job,
            )
            results = self._impl.run_worker_jobs(
                dispatch_jobs=dispatch_jobs,
                dispatch_plan=dispatch_plan,
                total_stocks=len(jobs),
                progress_callback=progress_callback,
                duckdb_data_mgr=data_mgr,
            )
        collected = self._impl.collect_stock_summaries(results)
        return PriceFactorExecuteContext(
            stock_summaries=collected["stock_summaries"],
            aggregate_profiler=collected["aggregate_profiler"],
        )

    def postprocess(
        self,
        preprocessed: PriceFactorPreprocessContext,
        executed: PriceFactorExecuteContext,
    ) -> Dict[str, object]:
        session_summary = self._impl.build_session_summary(
            stock_summaries=executed.stock_summaries,
            base_output_version_dir=preprocessed.base_output_version_dir,
            output_root=preprocessed.output_root,
            output_version_dir=preprocessed.output_version_dir,
            output_version_id=preprocessed.output_version_id,
        )
        if not session_summary:
            return {}
        from core.modules.data_manager import DataManager
        from core.modules.strategy.engines.shared.helpers.backtest_date_resolve import (
            resolve_backtest_period_payload,
            resolve_latest_completed_trading_date,
        )

        data_mgr = DataManager(is_verbose=False)
        session_summary["backtest_period"] = resolve_backtest_period_payload(
            settings_view=preprocessed.base_settings,
            stock_ids=sorted(preprocessed.stock_files.keys()),
            data_manager=data_mgr,
            latest_completed_trading_date=resolve_latest_completed_trading_date(data_mgr),
        )
        self._impl.save_session_outputs(
            strategy_name=preprocessed.strategy_name,
            output_version_dir=preprocessed.output_version_dir,
            output_version_id=preprocessed.output_version_id,
            base_output_version_dir=preprocessed.base_output_version_dir,
            session_summary=session_summary,
            settings_snapshot=preprocessed.base_settings.to_dict(),
            simulation_effective=simulation_effective_snapshot(
                preprocessed.simulation_settings
            ),
            stock_summaries=executed.stock_summaries,
        )
        self._impl.save_performance_report(
            output_version_dir=preprocessed.output_version_dir,
            aggregate_profiler=executed.aggregate_profiler,
        )
        self._impl.run_analyzer_hook(
            strategy_name=preprocessed.strategy_name,
            output_version_dir=preprocessed.output_version_dir,
            raw_settings=preprocessed.base_settings.to_dict(),
        )
        from core.modules.strategy.services.data.output.simulation_output_retention import (
            prune_disk_output_after_sim_run,
        )

        prune_disk_output_after_sim_run(
            preprocessed.strategy_name,
            "price",
            preprocessed.base_settings.to_dict(),
            protect_output_version_dir=preprocessed.output_version_dir.name,
        )
        return session_summary


__all__ = ["PriceFactorFlow"]
