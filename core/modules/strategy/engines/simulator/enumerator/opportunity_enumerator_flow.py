#!/usr/bin/env python3
"""Opportunity enumerator flow."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from core.modules.strategy.engines.simulator.base_flow import BaseSimulationFlow
from core.modules.strategy.engines.simulator.enumerator.opportunity_enumerator_flow_impl import (
    OpportunityEnumeratorFlowImpl,
)
from core.modules.strategy.enums import ReuseAction
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
        force_refresh: bool = False,
    ) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.stock_list = stock_list
        self.max_workers = max_workers
        self.base_settings = base_settings
        self.force_refresh = force_refresh
        self._impl = OpportunityEnumeratorFlowImpl(
            start_date=start_date,
            end_date=end_date,
            stock_list=stock_list,
            max_workers=max_workers,
            base_settings=base_settings,
            force_refresh=force_refresh,
        )

    def preprocess(
        self,
        *,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"],
    ) -> EnumeratorPreprocessContext:
        # step1: resolve runtime workers and load settings
        resolved_workers = self._impl.resolve_runtime_workers()
        base_settings = self._impl.load_settings(
            strategy_name=strategy_name, strategy_info=strategy_info
        )
        # step2: parse settings and resolve worker blueprint
        worker_ref = self._impl.resolve_worker_blueprint(
            strategy_name=strategy_name, strategy_info=strategy_info
        )
        enum_settings = self._impl.parse_enum_settings(base_settings)
        settings_payload = enum_settings.to_dict()
        request_fingerprint = self._impl.build_request_fingerprint(
            strategy_name=strategy_name,
            settings_payload=settings_payload,
            stock_ids=self.stock_list,
            worker_ref=worker_ref,
        )
        if self.force_refresh:
            reuse_plan = self._impl.build_force_rebuild_plan(request_fingerprint)
        else:
            reuse_plan = self._impl.plan_reuse(
                strategy_name=strategy_name,
                enum_settings=enum_settings,
                request_fingerprint=request_fingerprint,
            )
        if reuse_plan["action"] == ReuseAction.REUSE_FULL:
            return EnumeratorPreprocessContext(
                strategy_name=strategy_name,
                reuse_action=ReuseAction.REUSE_FULL,
                not_reused_because=reuse_plan["not_reused_because"],
                reuse_version_dir=reuse_plan["version_dir"],
                request_fingerprint=request_fingerprint,
            )
        # step3: create output version and build stock jobs
        if reuse_plan["action"] == ReuseAction.RUN_DIFF_STOCKS:
            version_info = self._impl.version_info_from_dir(reuse_plan["version_dir"])
        else:
            version_info = self._impl.create_output_version(
                strategy_name=strategy_name, enum_settings=enum_settings
            )
        target_stocks = (
            reuse_plan["missing_stock_ids"]
            if reuse_plan["action"] == ReuseAction.RUN_DIFF_STOCKS
            else self.stock_list
        )
        jobs = self._impl.build_jobs(
            strategy_name=strategy_name,
            settings_payload=settings_payload,
            output_dir=version_info["output_dir"],
            worker_ref=worker_ref,
            stock_ids=target_stocks,
        )
        result_fingerprint = self._impl.build_request_fingerprint(
            strategy_name=strategy_name,
            settings_payload=settings_payload,
            stock_ids=target_stocks,
            worker_ref=worker_ref,
        )
        # step4: preload global cache and init runtime context
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
            reuse_action=reuse_plan["action"],
            not_reused_because=reuse_plan["not_reused_because"],
            reuse_version_dir=reuse_plan["version_dir"],
            cached_fingerprint=reuse_plan["cached_fingerprint"],
            missing_stock_ids=reuse_plan["missing_stock_ids"],
        )

    def execute(self, preprocessed: EnumeratorPreprocessContext) -> EnumeratorExecuteContext:
        if preprocessed.reuse_action == ReuseAction.REUSE_FULL:
            return EnumeratorExecuteContext(reused=True)
        # step1: run scheduled jobs with memory-aware batching
        job_results = self._impl.run_jobs(
            jobs=preprocessed.jobs or [],
            global_extra_cache=preprocessed.global_extra_cache or {},
            max_workers=preprocessed.max_workers or 1,
            enum_settings=preprocessed.enum_settings,
        )
        # step2: return raw execution artifacts for postprocess
        return EnumeratorExecuteContext(job_results=job_results)

    def postprocess(
        self, preprocessed: EnumeratorPreprocessContext, executed: EnumeratorExecuteContext
    ) -> List[Dict[str, Any]]:
        if preprocessed.reuse_action == ReuseAction.REUSE_FULL:
            return self._impl.build_reuse_summary(
                strategy_name=preprocessed.strategy_name,
                version_dir=preprocessed.reuse_version_dir,
                reuse_action=ReuseAction.REUSE_FULL,
                not_reused_because=preprocessed.not_reused_because,
            )
        # step1: aggregate success/failure/opportunity stats
        aggregate = self._impl.aggregate_job_results(
            job_results=executed.job_results or [],
            aggregate_profiler=preprocessed.aggregate_profiler,
        )
        result_fingerprint = preprocessed.result_fingerprint
        if (
            preprocessed.reuse_action == ReuseAction.RUN_DIFF_STOCKS
            and preprocessed.cached_fingerprint is not None
        ):
            result_fingerprint = self._impl.merge_diff_fingerprint(
                cached_fingerprint=preprocessed.cached_fingerprint,
                newly_successful_stock_ids=aggregate.get("success_stock_ids") or [],
            )
        # step2: persist performance and metadata artifacts
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
            reuse_action=preprocessed.reuse_action,
            not_reused_because=preprocessed.not_reused_because,
        )
        # step3: cleanup old versions and return run summary
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
            reuse_action=preprocessed.reuse_action,
            not_reused_because=preprocessed.not_reused_because,
            diff_stock_count=(
                len(preprocessed.missing_stock_ids or [])
                if preprocessed.reuse_action == ReuseAction.RUN_DIFF_STOCKS
                else None
            ),
        )


__all__ = ["OpportunityEnumeratorFlow"]
