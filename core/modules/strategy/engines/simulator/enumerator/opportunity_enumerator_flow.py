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
    EnumeratorProbeContext,
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
        force_refresh: bool = False,
    ) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.stock_list = stock_list
        self.max_workers = max_workers
        self.base_settings = base_settings
        self.last_snapshot_id: int = 0
        self.last_run_used_db_cache: bool = False
        self._impl = OpportunityEnumeratorFlowImpl(
            start_date=start_date,
            end_date=end_date,
            stock_list=stock_list,
            max_workers=max_workers,
            base_settings=base_settings,
            workbench_strategy_name=workbench_strategy_name,
            workbench_run_id=workbench_run_id,
            force_refresh=force_refresh,
        )

    def run(
        self,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"] = None,
    ) -> Any:
        """
        指纹探针 → **仅当 DbCache 指纹解析完全成功时** 尝试命中表缓存 → 否则完整
        preprocess → execute → postprocess → **成功后再解析指纹并回写缓存**。

        命中缓存时跳过输出目录、worker 池与任务构建；``force_refresh`` 时跳过读缓存但仍可写缓存。
        """
        # Deferred import: ``cache`` / ``simulator_res_db_cache`` / ``DataManager`` 避免与枚举器初始化循环依赖。
        from core.modules.data_manager import DataManager
        from core.modules.strategy.services.cache.simulator_res_db_cache.snapshot_slot_adapters import (
            lookup_enum_cache,
            persist_enum_snapshot,
        )
        from core.modules.strategy.services.cache.simulator_res_db_cache.finger_print.finger_print import (
            resolve_db_cache_fingerprints,
        )

        self.last_snapshot_id = 0
        self.last_run_used_db_cache = False
        probe = self._preprocess_probe(strategy_name=strategy_name, strategy_info=strategy_info)

        data_mgr = DataManager(is_verbose=False)
        latest_completed_trading_date = str(
            data_mgr.service.calendar.get_latest_completed_trading_date() or ""
        ).strip()

        resolved_probe = resolve_db_cache_fingerprints(
            strategy_name=str(strategy_name),
            raw_settings=dict(probe.settings_for_fingerprint or {}),
            stock_list=list(self.stock_list or []),
            latest_completed_trading_date=latest_completed_trading_date,
        )

        # 指纹条件不足（settings / env / worker 等）时不走读缓存，直接跑完整 flow。
        if resolved_probe is not None and not self._impl.force_refresh:
            hit = lookup_enum_cache(
                strategy_name,
                resolved_probe.settings_fp,
                resolved_probe.env_fp,
            )
            if hit:
                summary_list, snapshot_id = hit
                self.last_snapshot_id = int(snapshot_id or 0)
                self.last_run_used_db_cache = True
                # 缓存命中不跑 worker，原无中间进度落盘；工作台 GET progress 在内存丢失时会读此文件，故在此写入终态。
                wn = self._impl.workbench_strategy_name
                wr = self._impl.workbench_run_id
                if wn and wr:
                    from core.modules.strategy.services.progress import ProgressRecorder

                    sn, rid = str(wn).strip(), str(wr).strip()
                    rec = ProgressRecorder.for_strategy_run_step(sn, rid, "enum")
                    sid = int(snapshot_id or 0)
                    rec.record(
                        {
                            "strategy_name": sn,
                            "run_id": rid,
                            "step_name": "enum",
                            "phase": "cache_hit",
                            "done_jobs": 0,
                            "total_jobs": 0,
                            "progress_pct": 100,
                            "snapshot_id": sid,
                        }
                    )
                return summary_list

        preprocessed = self._preprocess_finish(probe)
        executed = self.execute(preprocessed)
        summary_list = self.postprocess(preprocessed, executed)

        # Flow 完成后用与 DbCache 一致的解析路径再算指纹并落库（run 内 settings 可能与 probe 略有差异）。
        if summary_list and isinstance(summary_list, list):
            raw_for_resolve = dict(preprocessed.full_settings_snapshot_api or probe.settings_for_fingerprint or {})
            resolved_save = resolve_db_cache_fingerprints(
                strategy_name=str(strategy_name),
                raw_settings=raw_for_resolve,
                stock_list=list(self.stock_list or []),
                latest_completed_trading_date=latest_completed_trading_date,
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
                self.last_snapshot_id = int(persisted_sid or 0)
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
        worker_ref = self._impl.resolve_worker_blueprint(
            strategy_name=strategy_name, strategy_info=strategy_info
        )
        enum_settings = self._impl.parse_enum_settings(base_settings)
        settings_payload = enum_settings.to_dict()
        raw_full = copy.deepcopy(base_settings.to_dict())
        # API 形态转换器未接入时使用 runtime 快照（与校验 / 指纹路径同源 dict）。
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
            enum_settings=enum_settings,
            settings_payload=settings_payload,
            settings_for_fingerprint=settings_for_fingerprint,
            full_settings_snapshot_api=full_settings_snapshot_api,
            request_fingerprint=request_fingerprint,
            worker_ref=worker_ref,
        )

    def _preprocess_finish(self, probe: EnumeratorProbeContext) -> EnumeratorPreprocessContext:
        resolved_workers = self._impl.resolve_runtime_workers()
        version_info = self._impl.create_output_version(
            strategy_name=probe.strategy_name, enum_settings=probe.enum_settings
        )
        jobs = self._impl.build_jobs(
            strategy_name=probe.strategy_name,
            settings_payload=probe.settings_payload,
            output_dir=version_info["output_dir"],
            worker_ref=probe.worker_ref,
            stock_ids=self.stock_list,
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
            start_time=runtime["start_time"],
            aggregate_profiler=runtime["aggregate_profiler"],
        )

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
        self._impl.cleanup_versions(
            output_dir=preprocessed.output_dir,
            strategy_name=preprocessed.strategy_name,
            enum_settings=preprocessed.enum_settings,
        )
        return summary_list


__all__ = ["OpportunityEnumeratorFlow"]
