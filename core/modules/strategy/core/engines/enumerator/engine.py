"""枚举器引擎：preprocess → execute → postprocess（薄路由）。"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from core.modules.strategy.core.services.data.entity_data import GlobalDataPreloader
from core.modules.strategy.core.services.data.output_recorder import EnumeratorOutputRecorder
from core.modules.strategy.core.services.settings.settings_merge import StrategySettingsMerge

from .entity_based.context.runtime import EntityBasedRuntimeContext
from .entity_based.context.status import EntityBasedRuntimeStatus
from .entity_based.pipeline import EntityBasedJobPipeline, EntityBasedWorkerContext
from .entity_based.resolver.jobs import EntityBasedJobs
from .shared.fingerprint import EnumeratorExecutionMode, EnumeratorFingerprint
from .shared.report.statistics import EnumeratorReportStatistics
from .shared.runtime import EnumeratorRuntime
from .slice_based.context.runtime import SliceBasedRuntimeContext
from .slice_based.context.status import SliceBasedRuntimeStatus
from .slice_based.pipeline import SliceBasedJobPipeline, SliceBasedWorkerContext
from .slice_based.resolver.jobs import SliceBasedJobs

logger = logging.getLogger(__name__)


@dataclass
class EnumeratorEngine:
    """枚举编排入口。"""

    strategy_name: str
    output_dir: Path
    version_id: int
    version_dir_name: str
    start_date: str
    end_date: str
    entity_ids: List[str]
    disk_settings: Dict[str, Any]
    user_settings: Dict[str, Any]

    def run(self, strategy_info: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(
            "Starting enumeration: strategy=%s, entities=%d, dates=%s~%s",
            self.strategy_name,
            len(self.entity_ids),
            self.start_date,
            self.end_date,
        )

        runtime = self._build_runtime(strategy_info=strategy_info)
        ctx = runtime.context

        recorder = EnumeratorOutputRecorder(
            output_dir=self.output_dir,
            strategy_name=self.strategy_name,
            version_id=self.version_id,
            version_dir_name=self.version_dir_name,
        )
        recorder.save_preprocess_intermediate(
            fingerprint={"hash": ctx.fingerprint_hash},
            jobs=ctx.jobs,
            settings_diff=ctx.settings_diff,
        )

        global_data, global_meta = GlobalDataPreloader.preload(
            settings=StrategySettingsMerge.merge(ctx.disk_settings, ctx.settings_diff),
            start_date=self.start_date,
            end_date=self.end_date,
            entity_ids=self.entity_ids,
        )
        ctx.global_data_meta.update(global_meta)

        job_results = self._execute(runtime, global_data=global_data)

        for job_result in job_results:
            for stock_id, opportunities in self._iter_opportunities_from_job_result(job_result):
                if stock_id and opportunities:
                    recorder.save_stock_opportunities(stock_id, opportunities)

        report_template = EnumeratorReportStatistics.compute_from_dir(
            self.output_dir,
            total_stocks_hint=len(self.entity_ids),
        )

        runtime.status.stage = "postprocess"
        metadata = {
            "strategy_name": self.strategy_name,
            "version_id": self.version_id,
            "version_dir_name": self.version_dir_name,
            "fingerprint_hash": ctx.fingerprint_hash,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "total_stocks": len(self.entity_ids),
            "execution_mode": ctx.execution_mode,
            "status": "completed",
        }

        recorder.save_postprocess_intermediate(
            metadata=metadata,
            report=EnumeratorReportStatistics.to_bff_payload(
                report_template,
                include_stock_rows=False,
            ),
        )

        logger.info(
            "Enumeration completed: opportunities=%d, trigger_stocks=%d",
            report_template.total_opportunities,
            report_template.trigger_stocks,
        )

        return {
            "success": True,
            "total_opportunities": report_template.total_opportunities,
            "trigger_stocks": report_template.trigger_stocks,
            "fingerprint_hash": ctx.fingerprint_hash,
            "execution_mode": ctx.execution_mode,
        }

    def _build_runtime(
        self,
        *,
        strategy_info: Dict[str, Any],
        global_data_meta: Optional[Dict[str, Any]] = None,
    ) -> EnumeratorRuntime:
        settings_diff = StrategySettingsMerge.diff_for_fingerprint(
            self.disk_settings, self.user_settings
        )
        effective_settings = StrategySettingsMerge.merge(self.disk_settings, settings_diff)
        execution_mode = EnumeratorExecutionMode.resolve(effective_settings)

        fingerprint_hash = EnumeratorFingerprint.calculate_fingerprint_hash(
            settings_diff,
            self.entity_ids,
            self.start_date,
            self.end_date,
        )

        worker_ref = {
            "worker_module_path": strategy_info["worker_module_path"],
            "worker_class_name": strategy_info["worker_class_name"],
            "worker_file_path": str(strategy_info.get("worker_file_path") or ""),
        }

        jobs = self._build_jobs(
            execution_mode=execution_mode,
            effective_settings=effective_settings,
            worker_ref=worker_ref,
        )

        if execution_mode == EnumeratorExecutionMode.SLICE_BASED:
            context_cls = SliceBasedRuntimeContext
            status_cls = SliceBasedRuntimeStatus
        else:
            context_cls = EntityBasedRuntimeContext
            status_cls = EntityBasedRuntimeStatus

        context = context_cls(
            strategy_name=self.strategy_name,
            execution_mode=execution_mode,
            start_date=self.start_date,
            end_date=self.end_date,
            jobs=jobs,
            output_dir=self.output_dir,
            version_id=self.version_id,
            version_dir_name=self.version_dir_name,
            fingerprint_hash=fingerprint_hash,
            settings_diff=settings_diff,
            disk_settings=dict(self.disk_settings),
            worker_ref=worker_ref,
            global_data_meta=dict(global_data_meta or {}),
            task_name=f"enum_{self.strategy_name}",
            run_name=f"enum_{self.strategy_name}",
            performance=self._performance_for_mode(execution_mode),
        )
        return EnumeratorRuntime(context=context, status=status_cls(stage="preprocess"))

    def _build_jobs(
        self,
        *,
        execution_mode: str,
        effective_settings: Dict[str, Any],
        worker_ref: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        if execution_mode == EnumeratorExecutionMode.SLICE_BASED:
            return SliceBasedJobs.build(
                strategy_name=self.strategy_name,
                settings_payload=effective_settings,
                output_dir=str(self.output_dir),
                worker_ref=worker_ref,
                entity_ids=self.entity_ids,
                start_date=self.start_date,
                end_date=self.end_date,
            )
        return EntityBasedJobs.build(
            strategy_name=self.strategy_name,
            settings_payload=effective_settings,
            output_dir=str(self.output_dir),
            worker_ref=worker_ref,
            stock_ids=self.entity_ids,
            start_date=self.start_date,
            end_date=self.end_date,
        )

    @staticmethod
    def _performance_for_mode(execution_mode: str) -> Dict[str, Any]:
        if execution_mode == EnumeratorExecutionMode.SLICE_BASED:
            return SliceBasedWorkerContext.performance()
        return EntityBasedWorkerContext.performance()

    @classmethod
    def _execute(
        cls,
        runtime: EnumeratorRuntime,
        *,
        global_data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        on_job_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> List[Any]:
        mode = runtime.context.execution_mode
        runtime.status.stage = "execute"
        payload = global_data if global_data is not None else {}

        if mode == EnumeratorExecutionMode.SLICE_BASED:
            return SliceBasedJobPipeline.run(
                runtime,
                global_data=payload,
                on_job_progress=on_job_progress,
            )

        total_jobs = cls._entity_count_from_jobs(runtime.context.jobs)
        return EntityBasedJobPipeline.run(
            runtime,
            global_data=payload,
            total_jobs=total_jobs,
            on_job_progress=on_job_progress,
        )

    @staticmethod
    def _entity_count_from_jobs(jobs: List[Dict[str, Any]]) -> int:
        total = 0
        for job in jobs:
            stock_ids = job.get("stock_ids")
            if isinstance(stock_ids, list) and stock_ids:
                total += len(stock_ids)
            elif job.get("stock_id"):
                total += 1
        return max(total, len(jobs))

    @staticmethod
    def _iter_opportunities_from_job_result(job_result: Any):
        status = getattr(job_result, "status", None)
        status_value = getattr(status, "value", str(status))
        if str(status_value).lower() != "completed":
            return

        result_payload = getattr(job_result, "result", None) or {}
        if not isinstance(result_payload, dict):
            return

        if result_payload.get("bulk") and isinstance(result_payload.get("stock_results"), list):
            for row in result_payload["stock_results"]:
                if not isinstance(row, dict):
                    continue
                stock_id = str(row.get("stock_id") or "").strip()
                if not stock_id:
                    continue
                opportunities = row.get("opportunities")
                if not isinstance(opportunities, list):
                    raise ValueError(f"job_result.stock_results[{stock_id!r}] 缺少 opportunities list")
                yield stock_id, opportunities
            return

        stock_id = str(result_payload.get("stock_id") or "").strip()
        if not stock_id:
            raise ValueError("entity_based job_result 缺少 stock_id")
        opportunities = result_payload.get("opportunities")
        if not isinstance(opportunities, list):
            raise ValueError(f"job_result[{stock_id}] 缺少 opportunities list")
        yield stock_id, opportunities


__all__ = ["EnumeratorEngine"]
