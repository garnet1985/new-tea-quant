#!/usr/bin/env python3
"""Opportunity enumerator flow."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from core.modules.strategy.engines.simulator.base_flow import BaseSimulationFlow
from core.modules.strategy.engines.simulator.enumerator.opportunity_enumerator_flow_impl import (
    OpportunityEnumeratorFlowImpl,
)
from core.modules.strategy.engines.simulator.enumerator.data_classes import (
    EnumeratorExecuteContext,
    EnumeratorPreprocessContext,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )


class OpportunityEnumeratorFlow(BaseSimulationFlow):
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
    ) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.stock_list = stock_list
        self.max_workers = max_workers
        self.base_settings = base_settings
        self._impl = OpportunityEnumeratorFlowImpl(
            start_date=start_date,
            end_date=end_date,
            stock_list=stock_list,
            max_workers=max_workers,
            base_settings=base_settings,
            workbench_strategy_name=workbench_strategy_name,
            workbench_run_id=workbench_run_id,
        )

    def preprocess(
        self,
        *,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"],
    ) -> EnumeratorPreprocessContext:
        base_settings = self._impl.load_settings(
            strategy_name=strategy_name, strategy_info=strategy_info
        )
        worker_ref = self._impl.resolve_worker_blueprint(
            strategy_name=strategy_name, strategy_info=strategy_info
        )
        enum_settings = self._impl.parse_enum_settings(base_settings)
        settings_payload = enum_settings.to_dict()
        settings_for_fingerprint = copy.deepcopy(base_settings.to_dict())
        request_fingerprint = self._impl.build_request_fingerprint(
            strategy_name=strategy_name,
            settings_payload=settings_for_fingerprint,
            stock_ids=self.stock_list,
            worker_ref=worker_ref,
        )
        resolved_workers = self._impl.resolve_runtime_workers()
        version_info = self._impl.create_output_version(
            strategy_name=strategy_name, enum_settings=enum_settings
        )
        jobs = self._impl.build_jobs(
            strategy_name=strategy_name,
            settings_payload=settings_payload,
            output_dir=version_info["output_dir"],
            worker_ref=worker_ref,
            stock_ids=self.stock_list,
        )
        result_fingerprint = self._impl.build_request_fingerprint(
            strategy_name=strategy_name,
            settings_payload=settings_for_fingerprint,
            stock_ids=self.stock_list,
            worker_ref=worker_ref,
        )
        global_extra_cache = self._impl.preload_global_cache(settings_payload, jobs)
        runtime = self._impl.create_runtime_context()
        return EnumeratorPreprocessContext(
            strategy_name=strategy_name,
            enum_settings=enum_settings,
            settings_payload=settings_payload,
            request_fingerprint=request_fingerprint,
            result_fingerprint=result_fingerprint,
            output_dir=version_info["output_dir"],
            version_id=version_info["version_id"],
            version_dir_name=version_info["version_dir_name"],
            jobs=jobs,
            global_extra_cache=global_extra_cache,
            max_workers=resolved_workers,
            start_time=runtime["start_time"],
            aggregate_profiler=runtime["aggregate_profiler"],
        )

    def execute(self, preprocessed: EnumeratorPreprocessContext) -> EnumeratorExecuteContext:
        job_results = self._impl.run_jobs(
            jobs=preprocessed.jobs or [],
            global_extra_cache=preprocessed.global_extra_cache or {},
            max_workers=preprocessed.max_workers or 1,
            enum_settings=preprocessed.enum_settings,
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
        self._impl.save_metadata(
            strategy_name=preprocessed.strategy_name,
            output_dir=preprocessed.output_dir,
            version_id=preprocessed.version_id,
            version_dir_name=preprocessed.version_dir_name,
            opportunity_count=aggregate["total_opportunities"],
            settings_snapshot=preprocessed.settings_payload,
            enum_settings=preprocessed.enum_settings,
            fingerprint=result_fingerprint,
            status="completed",
        )
        self._impl.cleanup_versions(
            output_dir=preprocessed.output_dir,
            strategy_name=preprocessed.strategy_name,
            enum_settings=preprocessed.enum_settings,
        )
        return self._impl.build_result_summary(
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
        )


__all__ = ["OpportunityEnumeratorFlow"]
