#!/usr/bin/env python3
"""枚举器 flow 基类：settings 收集 → 子类 build job → shared 产出。"""

from __future__ import annotations

import copy
import logging
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from core.modules.strategy.engines.simulator.base_flow import BaseSimulationFlow
from core.modules.strategy.engines.simulator.enumerator.shared import (
    EnumeratorExecuteContext,
    EnumeratorPreprocessContext,
    EnumeratorProbeContext,
)
from core.modules.strategy.engines.simulator.enumerator.shared.settings import (
    EnumeratorSettings,
)
from core.modules.strategy.engines.simulator.enumerator.shared.services import (
    EnumeratorSharedServices,
)
from core.modules.strategy.engines.shared.data_classes.market_profile_context import (
    MarketProfileContext,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.shared.helpers.simulation_flow import (
    prepare_simulation_settings,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )
    from core.modules.strategy.execution_manager.workbench_flow_progress import (
        WorkbenchFlowProgress,
    )


class BaseEnumeratorFlow(BaseSimulationFlow):
    """Shared：probe / execute / postprocess；子类实现 ``_preprocess_finish``（build job）。"""

    _impl: EnumeratorSharedServices

    def __init__(
        self,
        *,
        start_date: str,
        end_date: str,
        stock_list: List[str],
        max_workers: Union[str, int],
        base_settings: Optional[StrategySettingsView],
        workbench_strategy_name: Optional[str] = None,
        workbench_run_id: Optional[str] = None,
        force_refresh: bool = False,
        backtest_period: Optional[Dict[str, str]] = None,
    ) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.stock_list = stock_list
        self.max_workers = max_workers
        self.base_settings = base_settings
        self.last_version: int = 0
        self.used_db_cache: bool = False
        self.workbench_strategy_name = workbench_strategy_name
        self.workbench_run_id = workbench_run_id
        self.force_refresh = force_refresh
        self._backtest_period = backtest_period

    def run(
        self,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"] = None,
        *,
        workbench_progress: Optional["WorkbenchFlowProgress"] = None,
    ) -> Any:
        from core.modules.data_manager import DataManager
        from core.modules.strategy.engines.shared.helpers.backtest_date_resolve import (
            resolve_latest_completed_trading_date,
        )
        from core.modules.strategy.services.cache.simulator_res_db_cache.finger_print.finger_print import (
            resolve_db_cache_fingerprints,
        )
        from core.modules.strategy.services.cache.simulator_res_db_cache.snapshot_slot_adapters import (
            lookup_enum_cache,
            persist_enum_snapshot,
        )

        self.last_version = 0
        self.used_db_cache = False
        wp = workbench_progress
        if wp is not None:
            wp.stage("load", 0.05)
        probe = self._preprocess_probe(strategy_name=strategy_name, strategy_info=strategy_info)

        data_mgr = DataManager(is_verbose=False)
        latest_completed_trading_date = resolve_latest_completed_trading_date(data_mgr)

        resolved_probe = resolve_db_cache_fingerprints(
            strategy_name=str(strategy_name),
            raw_settings=dict(probe.settings_for_fingerprint or {}),
            stock_list=list(self.stock_list or []),
            latest_completed_trading_date=latest_completed_trading_date,
            data_manager=data_mgr,
            env_start_date=self.start_date,
            env_end_date=self.end_date,
        )

        if wp is not None:
            wp.stage("load", 0.85)

        if resolved_probe is not None and not self._impl.force_refresh:
            hit = lookup_enum_cache(
                strategy_name,
                resolved_probe.settings_fp,
                resolved_probe.env_fp,
            )
            if hit:
                summary_list, wb_version = hit
                self.last_version = int(wb_version or 0)
                self.used_db_cache = True
                total_opps = 0
                if summary_list and isinstance(summary_list[0], dict):
                    total_opps = int(summary_list[0].get("opportunities", 0) or 0)
                out_dir = ""
                if summary_list and isinstance(summary_list[0], dict):
                    out_dir = str(summary_list[0].get("enumerator_output_dir") or "").strip()
                logger.info(
                    "枚举 DbCache 命中 · strategy=%s · version=%s · dir=%s · opportunities=%s "
                    "（未跑 worker；改 settings/切库后请 -f/--force）",
                    strategy_name,
                    wb_version,
                    out_dir or "—",
                    total_opps,
                )
                from core.modules.strategy.services.data.output.simulation_output_retention import (
                    prune_disk_outputs_for_strategy,
                )

                prune_disk_outputs_for_strategy(
                    strategy_name,
                    dict(probe.settings_for_fingerprint or {}),
                )
                wn = self._impl.workbench_strategy_name
                wr = self._impl.workbench_run_id
                if wn and wr:
                    from core.modules.strategy.services.progress import ProgressRecorder

                    sn, rid = str(wn).strip(), str(wr).strip()
                    rec = ProgressRecorder.for_strategy_run_step(sn, rid, "enum")
                    sid = int(wb_version or 0)
                    rec.record(
                        {
                            "strategy_name": sn,
                            "run_id": rid,
                            "step_name": "enum",
                            "phase": "cache_hit",
                            "done_jobs": 0,
                            "total_jobs": 0,
                            "progress_pct": 100,
                            "version": sid,
                        }
                    )
                if wp is not None:
                    wp.stage("report", 1.0)
                return summary_list

        if wp is not None:
            wp.stage("load", 1.0)
            wp.stage("dispatch", 0.05)
        preprocessed = self._preprocess_finish(probe)
        if wp is not None:
            wp.stage("dispatch", 1.0)
            wp.stage("execute", 0.0)
        executed = self.execute(preprocessed)
        if wp is not None:
            wp.stage("execute", 1.0)
        if wp is not None:
            wp.stage("report", 0.2)
        summary_list = self.postprocess(preprocessed, executed)

        if summary_list and isinstance(summary_list, list):
            raw_for_resolve = dict(
                preprocessed.full_settings_snapshot_api or probe.settings_for_fingerprint or {}
            )
            resolved_save = resolve_db_cache_fingerprints(
                strategy_name=str(strategy_name),
                raw_settings=raw_for_resolve,
                stock_list=list(self.stock_list or []),
                latest_completed_trading_date=latest_completed_trading_date,
                data_manager=data_mgr,
                env_start_date=self.start_date,
                env_end_date=self.end_date,
            )
            if resolved_save is not None:
                first = summary_list[0] if summary_list else {}
                persisted_sid = persist_enum_snapshot(
                    strategy_name,
                    settings_snapshot_api=dict(resolved_save.normalized_settings_dict or {}),
                    report_enum=first if isinstance(first, dict) else {},
                    settings_fingerprint_id=resolved_save.settings_fp,
                    env_fingerprint_id=resolved_save.env_fp,
                )
                self.last_version = int(persisted_sid or 0)
        return summary_list

    def _preprocess_probe(
        self,
        *,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"],
    ) -> EnumeratorProbeContext:
        base_settings = self._impl.load_settings(
            strategy_name=strategy_name, strategy_info=strategy_info
        )
        simulation_settings = prepare_simulation_settings(base_settings)
        market_profile = MarketProfileContext.from_settings_view(base_settings)
        worker_ref = self._impl.resolve_worker_blueprint(
            strategy_name=strategy_name, strategy_info=strategy_info
        )
        enum_settings = EnumeratorSettings.from_base(base_settings)
        settings_payload = enum_settings.to_dict()
        raw_full = copy.deepcopy(base_settings.to_dict())
        full_settings_snapshot_api = raw_full
        settings_for_fingerprint = copy.deepcopy(base_settings.to_dict())
        request_fingerprint = self._impl.build_request_fingerprint(
            strategy_name=strategy_name,
            settings_payload=settings_for_fingerprint,
            stock_ids=self.stock_list,
            worker_ref=worker_ref,
        )
        return EnumeratorProbeContext(
            strategy_name=strategy_name,
            market_profile=market_profile,
            simulation_settings=simulation_settings,
            enum_settings=enum_settings,
            settings_payload=settings_payload,
            settings_for_fingerprint=settings_for_fingerprint,
            full_settings_snapshot_api=full_settings_snapshot_api,
            request_fingerprint=request_fingerprint,
            worker_ref=worker_ref,
        )

    @abstractmethod
    def _preprocess_finish(self, probe: EnumeratorProbeContext) -> EnumeratorPreprocessContext:
        """Build jobs（stock / calendar 分支）。"""

    def preprocess(
        self,
        *,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"],
    ) -> EnumeratorPreprocessContext:
        probe = self._preprocess_probe(strategy_name=strategy_name, strategy_info=strategy_info)
        return self._preprocess_finish(probe)

    def execute(self, preprocessed: EnumeratorPreprocessContext) -> EnumeratorExecuteContext:
        job_results = self._impl.run_jobs(
            jobs=preprocessed.jobs or [],
            global_extra_cache=preprocessed.global_extra_cache or {},
            max_workers=preprocessed.max_workers or 1,
            enum_settings=preprocessed.enum_settings,
            duckdb_data_mgr=preprocessed.data_mgr,
        )
        return EnumeratorExecuteContext(job_results=job_results)

    def postprocess(
        self, preprocessed: EnumeratorPreprocessContext, executed: EnumeratorExecuteContext
    ) -> List[Dict[str, Any]]:
        aggregate = self._impl.aggregate_job_results(
            job_results=executed.job_results or [],
            aggregate_profiler=preprocessed.aggregate_profiler,
        )
        result_fingerprint = preprocessed.result_fingerprint
        self._impl.save_performance_report(
            output_dir=preprocessed.output_dir,
            success_count=aggregate["success_count"],
            aggregate_profiler=preprocessed.aggregate_profiler,
        )
        enum_bff_payload = self._impl.save_metadata(
            strategy_name=preprocessed.strategy_name,
            output_dir=preprocessed.output_dir,
            version_id=preprocessed.version_id,
            version_dir_name=preprocessed.version_dir_name,
            settings_snapshot=preprocessed.settings_payload,
            enum_settings=preprocessed.enum_settings,
            fingerprint=result_fingerprint,
            status="completed",
            simulation_settings=preprocessed.simulation_settings,
        )
        summary_list = self._impl.build_result_report(
            strategy_name=preprocessed.strategy_name,
            version_id=preprocessed.version_id,
            version_dir_name=preprocessed.version_dir_name,
            total_opportunities=aggregate["total_opportunities"],
            success_count=aggregate["success_count"],
            failed_count=aggregate["failed_count"],
            trigger_stock_count=aggregate["trigger_stock_count"],
            completed_count=aggregate["completed_count"],
            unfinished_count=aggregate["unfinished_count"],
            start_time=preprocessed.start_time,
            output_dir=preprocessed.output_dir,
            enum_bff_payload=enum_bff_payload,
        )
        from core.modules.strategy.services.data.output.simulation_output_retention import (
            prune_disk_output_after_sim_run,
        )

        prune_disk_output_after_sim_run(
            preprocessed.strategy_name,
            "enum",
            preprocessed.enum_settings.to_dict(),
            protect_output_version_dir=preprocessed.version_dir_name,
        )
        return summary_list


__all__ = ["BaseEnumeratorFlow"]
