#!/usr/bin/env python3
"""Calendar slice enumerator flow (MVP)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Union

from core.modules.strategy.engines.simulator.enumerator.calendar_slice.flow_impl import (
    CalendarSliceEnumeratorFlowImpl,
)
from core.modules.strategy.engines.simulator.enumerator.opportunity_enumerator_flow import (
    OpportunityEnumeratorFlow,
)

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )
    from core.modules.strategy.engines.simulator.enumerator.data_classes import (
        EnumeratorProbeContext,
        EnumeratorPreprocessContext,
    )


class CalendarSliceEnumeratorFlow(OpportunityEnumeratorFlow):
    """calendar_slice 编排：单 job、跳过分 dispatch 探针。"""

    def __init__(
        self,
        *,
        start_date: str,
        end_date: str,
        stock_list: List[str],
        max_workers: Union[str, int],
        base_settings: Optional[Any],
        workbench_strategy_name: Optional[str] = None,
        workbench_run_id: Optional[str] = None,
        force_refresh: bool = False,
        backtest_period: Optional[dict[str, str]] = None,
    ) -> None:
        super().__init__(
            start_date=start_date,
            end_date=end_date,
            stock_list=stock_list,
            max_workers=max_workers,
            base_settings=base_settings,
            workbench_strategy_name=workbench_strategy_name,
            workbench_run_id=workbench_run_id,
            force_refresh=force_refresh,
            backtest_period=backtest_period,
        )
        self._impl = CalendarSliceEnumeratorFlowImpl(
            start_date=start_date,
            end_date=end_date,
            stock_list=stock_list,
            max_workers=max_workers,
            base_settings=base_settings,
            workbench_strategy_name=workbench_strategy_name,
            workbench_run_id=workbench_run_id,
            force_refresh=force_refresh,
            backtest_period=backtest_period,
        )

    def _preprocess_finish(self, probe: "EnumeratorProbeContext") -> "EnumeratorPreprocessContext":
        from core.modules.data_manager import DataManager
        from core.modules.strategy.engines.shared.helpers.backtest_calendar_context import (
            build_backtest_calendar_context,
        )
        from core.modules.strategy.engines.shared.helpers.backtest_date_resolve import (
            BacktestDateRange,
        )
        from core.modules.strategy.engines.simulator.enumerator.data_classes import (
            EnumeratorPreprocessContext,
        )
        from core.infra.db.engines.duckdb.process_pool_scope import (
            ensure_data_manager_restored,
        )

        version_info = self._impl.create_output_version(
            strategy_name=probe.strategy_name, enum_settings=probe.enum_settings
        )
        mp_id = probe.market_profile.profile_id
        data_mgr = DataManager(is_verbose=False)
        calendar_ctx = build_backtest_calendar_context(
            data_manager=data_mgr,
            period=BacktestDateRange(
                self._impl.start_date,
                self._impl.end_date,
                "",
                "",
            ),
            market_profile_id=mp_id,
        )
        calendar_dict = calendar_ctx.to_dict()
        ensure_data_manager_restored(data_mgr)

        resolved_workers = self._impl.resolve_runtime_workers()
        jobs = self._impl.build_jobs(
            strategy_name=probe.strategy_name,
            settings_payload=probe.settings_payload,
            output_dir=version_info["output_dir"],
            worker_ref=probe.worker_ref,
            stock_ids=self.stock_list,
        )
        for job in jobs:
            job["market_profile_id"] = mp_id
            job["backtest_calendar"] = calendar_dict
        self._impl.enrich_calendar_dispatch_jobs(
            jobs,
            settings_payload=probe.settings_payload,
            calendar_dict=calendar_dict,
        )
        result_fingerprint = self._impl.build_request_fingerprint(
            strategy_name=probe.strategy_name,
            settings_payload=probe.settings_for_fingerprint,
            stock_ids=self.stock_list,
            worker_ref=probe.worker_ref,
        )
        global_extra_cache = self._impl.preload_global_cache(probe.settings_payload, jobs)
        runtime = self._impl.create_runtime_context()
        return EnumeratorPreprocessContext(
            strategy_name=probe.strategy_name,
            market_profile=probe.market_profile,
            simulation_settings=probe.simulation_settings,
            enum_settings=probe.enum_settings,
            full_settings_snapshot_api=probe.full_settings_snapshot_api,
            settings_payload=probe.settings_payload,
            request_fingerprint=probe.request_fingerprint,
            result_fingerprint=result_fingerprint,
            output_dir=version_info["output_dir"],
            version_id=version_info["version_id"],
            version_dir_name=version_info["version_dir_name"],
            jobs=jobs,
            global_extra_cache=global_extra_cache,
            max_workers=resolved_workers,
            data_mgr=data_mgr,
            start_time=runtime["start_time"],
            aggregate_profiler=runtime["aggregate_profiler"],
        )


__all__ = ["CalendarSliceEnumeratorFlow"]
