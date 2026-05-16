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
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
        StrategySettingsView,
    )


class _PriceFactorProbe(NamedTuple):
    """枚举输出解析完成后、尚未创建本次 price_factor 版本目录前的中间状态。"""

    strategy_name: str
    base_settings: "StrategySettingsView"
    simulator_config: Any
    output_version_dir: Path
    output_root: Path
    stock_files: Dict[str, Dict[str, Path]]


class PriceFactorFlow(BaseSimulationFlow):
    """Three-stage price factor simulation flow（支持 Simulator Res DB Cache）。"""

    def __init__(self, is_verbose: bool = False, *, force_refresh: bool = False) -> None:
        self._impl = PriceFactorFlowImpl(is_verbose=is_verbose)
        self._force_refresh = bool(force_refresh)
        self.last_snapshot_id: int = 0
        self.last_run_used_db_cache: bool = False

    def _probe(
        self,
        *,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"],
    ) -> _PriceFactorProbe:
        base_settings = self._impl.load_settings(strategy_name, strategy_info)
        simulator_config = self._impl.parse_config(base_settings)
        output_version_dir, output_root = self._impl.resolve_source_version(
            strategy_name=strategy_name,
            base_settings=base_settings,
            config=simulator_config,
            strategy_info=strategy_info,
        )
        stock_files = self._impl.scan_stock_files(output_version_dir)
        return _PriceFactorProbe(
            strategy_name=strategy_name,
            base_settings=base_settings,
            simulator_config=simulator_config,
            output_version_dir=output_version_dir,
            output_root=output_root,
            stock_files=stock_files,
        )

    def _finish_probe(self, probe: _PriceFactorProbe) -> PriceFactorPreprocessContext:
        sim_version_dir, sim_version_id = self._impl.create_simulation_version(
            probe.strategy_name
        )
        simulation_settings = prepare_simulation_settings(probe.base_settings)
        return PriceFactorPreprocessContext(
            strategy_name=probe.strategy_name,
            base_settings=probe.base_settings,
            simulation_settings=simulation_settings,
            simulator_config=probe.simulator_config,
            output_version_dir=probe.output_version_dir,
            output_root=probe.output_root,
            sim_version_dir=sim_version_dir,
            sim_version_id=sim_version_id,
            stock_files=probe.stock_files,
        )

    def run(
        self,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"] = None,
        *,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Any:
        """
        轻量 probe → 指纹解析成功则尝试 DbCache → 否则创建版本目录并
        preprocess（等价）→ execute → postprocess → 再写缓存。

        ``progress_callback``：工作台轮询用；传入 0～100 的磁盘进度百分比（完成前宜小于 100）。
        """
        from core.modules.data_manager import DataManager
        from core.modules.strategy.services.cache.simulator_res_db_cache.snapshot_slot_adapters import (
            lookup_price_factor_cache,
            persist_price_factor_snapshot,
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
        probe = self._probe(strategy_name=strategy_name, strategy_info=strategy_info)
        stock_list = stock_ids_for_db_cache_fingerprint(
            probe.output_version_dir,
            fallback_ids=sorted(probe.stock_files.keys()),
        )
        raw_for_fp = raw_settings_for_db_cache_fingerprint(
            probe.base_settings, strategy_info
        )

        data_mgr = DataManager(is_verbose=False)
        latest_completed_trading_date = str(
            data_mgr.stock.kline.load_latest_date("daily")
            or data_mgr.service.calendar.get_latest_completed_trading_date()
            or ""
        ).strip()

        resolved_probe = resolve_db_cache_fingerprints(
            strategy_name=str(strategy_name),
            raw_settings=raw_for_fp,
            stock_list=list(stock_list),
            latest_completed_trading_date=latest_completed_trading_date,
        )

        tick(10.0)
        if resolved_probe is not None and not self._force_refresh:
            hit = lookup_price_factor_cache(
                strategy_name,
                resolved_probe.settings_fp,
                resolved_probe.env_fp,
            )
            if hit:
                summary, snapshot_id = hit
                self.last_snapshot_id = int(snapshot_id or 0)
                self.last_run_used_db_cache = True
                tick(92.0)
                return summary

        tick(12.0)
        preprocessed = self._finish_probe(probe)
        tick(14.0)
        executed = self.execute(preprocessed, progress_callback=tick)
        tick(90.0)
        summary = self.postprocess(preprocessed, executed)
        tick(94.0)

        if summary and isinstance(summary, dict):
            raw_save = raw_settings_for_db_cache_fingerprint(
                preprocessed.base_settings, strategy_info
            )
            resolved_save = resolve_db_cache_fingerprints(
                strategy_name=str(strategy_name),
                raw_settings=raw_save,
                stock_list=list(stock_list),
                latest_completed_trading_date=latest_completed_trading_date,
            )
            if resolved_save is not None:
                sid = persist_price_factor_snapshot(
                    strategy_name,
                    settings_snapshot_api=dict(resolved_save.normalized_settings_dict or {}),
                    report_price_factor=summary,
                    settings_fingerprint_id=resolved_save.settings_fp,
                    env_fingerprint_id=resolved_save.env_fp,
                )
                self.last_snapshot_id = int(sid or 0)
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
        jobs = self._impl.build_worker_jobs(
            strategy_name=preprocessed.strategy_name,
            sim_version_dir=preprocessed.sim_version_dir,
            stock_files=preprocessed.stock_files,
            config=preprocessed.simulator_config,
        )
        sim_snap = simulation_effective_snapshot(preprocessed.simulation_settings)
        for job in jobs:
            cfg = dict(job.get("config") or {})
            cfg["simulation"] = sim_snap
            job["config"] = cfg
        results = self._impl.run_worker_jobs(
            jobs=jobs,
            max_workers=preprocessed.simulator_config.max_workers,
            progress_callback=progress_callback,
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
            output_version_dir=preprocessed.output_version_dir,
            output_root=preprocessed.output_root,
            sim_version_dir=preprocessed.sim_version_dir,
            sim_version_id=preprocessed.sim_version_id,
        )
        if not session_summary:
            return {}
        self._impl.save_session_outputs(
            strategy_name=preprocessed.strategy_name,
            sim_version_dir=preprocessed.sim_version_dir,
            sim_version_id=preprocessed.sim_version_id,
            output_version_dir=preprocessed.output_version_dir,
            session_summary=session_summary,
            settings_snapshot=preprocessed.base_settings.to_dict(),
            simulation_effective=simulation_effective_snapshot(
                preprocessed.simulation_settings
            ),
        )
        self._impl.save_performance_report(
            sim_version_dir=preprocessed.sim_version_dir,
            aggregate_profiler=executed.aggregate_profiler,
        )
        self._impl.run_analyzer_hook(
            strategy_name=preprocessed.strategy_name,
            sim_version_dir=preprocessed.sim_version_dir,
            raw_settings=preprocessed.base_settings.to_dict(),
        )
        return session_summary


__all__ = ["PriceFactorFlow"]
