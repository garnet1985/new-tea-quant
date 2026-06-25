#!/usr/bin/env python3
"""Stock-based（entity_timeline）枚举 flow。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from core.modules.strategy.engines.simulator.enumerator.shared import (
    EnumeratorPreprocessContext,
    EnumeratorProbeContext,
)
from core.modules.strategy.engines.simulator.enumerator.shared.flow import (
    BaseEnumeratorFlow,
)
from core.modules.strategy.engines.simulator.enumerator.shared.services import (
    EnumeratorSharedServices,
)
from core.modules.strategy.engines.simulator.enumerator.stock_based.progress import (
    enrich_entity_dispatch_jobs,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)


class StockBasedEnumeratorFlow(BaseEnumeratorFlow):
    """每股独立时间线：dispatch probe → 多 job → StockBasedEnumeratorWorker。"""

    _execution_mode_label = "stock_based"

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
        self._impl = EnumeratorSharedServices(
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

    def _preprocess_finish(self, probe: EnumeratorProbeContext) -> EnumeratorPreprocessContext:
        from core.modules.data_manager import DataManager
        from core.infra.db.engines.duckdb.process_pool_scope import (
            ensure_data_manager_restored,
        )
        from core.modules.strategy.engines.shared.helpers.backtest_calendar_context import (
            build_backtest_calendar_context,
        )
        from core.modules.strategy.engines.shared.helpers.backtest_date_resolve import (
            BacktestDateRange,
        )
        from core.modules.strategy.engines.simulator.enumerator.shared import (
            EnumeratorPreprocessContext,
        )
        from core.modules.strategy.services.execution.enum_dispatch import (
            maybe_run_enum_dispatch_probe,
            resolve_enum_dispatch_plan,
        )

        version_info = self._impl.create_output_version(
            strategy_name=probe.strategy_name,
            enum_settings=probe.enum_settings,
            fingerprint=probe.request_fingerprint,
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

        measured_mb = maybe_run_enum_dispatch_probe(
            strategy_name=probe.strategy_name,
            stock_ids=list(self.stock_list),
            settings_payload=probe.settings_payload,
            output_dir=version_info["output_dir"],
            worker_ref=probe.worker_ref,
            start_date=self._impl.start_date,
            end_date=self._impl.end_date,
            global_extra_cache={},
            market_profile_id=mp_id,
            backtest_calendar=calendar_dict,
            data_mgr=data_mgr,
        )
        ensure_data_manager_restored(data_mgr)
        dispatch_plan = resolve_enum_dispatch_plan(
            total_stocks=len(self.stock_list),
            measured_mb_per_entity=measured_mb,
        )
        jobs = self._impl.build_jobs(
            strategy_name=probe.strategy_name,
            settings_payload=probe.settings_payload,
            output_dir=version_info["output_dir"],
            worker_ref=probe.worker_ref,
            stock_ids=self.stock_list,
            entities_per_job=dispatch_plan.entities_per_job,
        )
        for job in jobs:
            job["market_profile_id"] = mp_id
            job["backtest_calendar"] = calendar_dict
        enrich_entity_dispatch_jobs(
            jobs,
            settings_payload=probe.settings_payload,
            workbench_strategy_name=self._impl.workbench_strategy_name,
            workbench_run_id=self._impl.workbench_run_id,
        )
        result_fingerprint = self._impl.build_request_fingerprint(
            strategy_name=probe.strategy_name,
            disk_settings=probe.disk_settings,  # 磁盘上的 settings
            user_modified_settings=probe.settings_for_fingerprint,  # 用户修改过的 settings
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
            max_workers=dispatch_plan.max_workers,
            data_mgr=data_mgr,
            start_time=runtime["start_time"],
            aggregate_profiler=runtime["aggregate_profiler"],
        )


__all__ = ["StockBasedEnumeratorFlow"]
