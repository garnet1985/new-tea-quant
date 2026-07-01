"""slice_based 主执行流程 — preprocess → BacktestEngine → postprocess。"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import BacktestJob, JobContext, JobReport, RunCallbacks, RunProgress
from core.modules.strategy.core.context.strategy_context import StrategyContext
from core.modules.strategy.core.services.data.entity_data import GlobalDataPreloader
from core.modules.strategy.core.services.data.output_recorder import EnumeratorOutputRecorder

from ..shared.opportunities import iter_opportunities_from_job_result
from ..shared.report.statistics import EnumeratorReportStatistics
from ..shared.runtime import EnumeratorRuntime, JobResultHelper
from .context.runtime import SliceBasedRuntimeContext
from .context.status import SliceBasedRuntimeStatus
from .resolver.jobs import SliceBasedJobs
from .worker import SliceBasedWorker

logger = logging.getLogger(__name__)


class SliceBasedJobPipeline:
    """slice_based 枚举完整流程。"""

    @classmethod
    def run(cls, strategy: StrategyContext) -> Dict[str, Any]:
        logger.info(
            "Starting enumeration: strategy=%s, entities=%d, dates=%s~%s",
            strategy.strategy_name,
            len(strategy.entity_ids),
            strategy.start_date,
            strategy.end_date,
        )

        runtime = cls.build_runtime(strategy)
        ctx = runtime.context

        recorder = EnumeratorOutputRecorder(
            output_dir=strategy.output_dir,
            strategy_name=strategy.strategy_name,
            version_id=strategy.version_id,
            version_dir_name=strategy.version_dir_name,
        )
        recorder.save_preprocess_intermediate(
            fingerprint={"hash": ctx.fingerprint_hash},
            jobs=ctx.jobs,
            settings_diff=ctx.settings_diff,
        )

        global_data, global_meta = GlobalDataPreloader.preload(
            settings=strategy.effective_settings.raw_settings,
            start_date=strategy.start_date,
            end_date=strategy.end_date,
            entity_ids=strategy.entity_ids,
        )
        ctx.global_data_meta.update(global_meta)

        runtime.status.stage = "execute"
        job_results = cls.execute_backtest(runtime, global_data=global_data)

        for job_result in job_results:
            for stock_id, opportunities in iter_opportunities_from_job_result(job_result):
                if stock_id and opportunities:
                    recorder.save_stock_opportunities(stock_id, opportunities)

        report_template = EnumeratorReportStatistics.compute_from_dir(
            strategy.output_dir,
            total_stocks_hint=len(strategy.entity_ids),
        )

        runtime.status.stage = "postprocess"
        metadata = {
            "strategy_name": strategy.strategy_name,
            "version_id": strategy.version_id,
            "version_dir_name": strategy.version_dir_name,
            "fingerprint_hash": ctx.fingerprint_hash,
            "start_date": strategy.start_date,
            "end_date": strategy.end_date,
            "total_stocks": len(strategy.entity_ids),
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

    @classmethod
    def build_runtime(
        cls,
        strategy: StrategyContext,
        *,
        global_data_meta: Optional[Dict[str, Any]] = None,
    ) -> EnumeratorRuntime:
        settings = strategy.effective_settings

        if not settings.is_slice_based:
            raise ValueError(
                f"SliceBasedJobPipeline 期望 slice_based，实际 {settings.execution_mode!r}"
            )

        jobs = SliceBasedJobs.build(
            strategy_name=strategy.strategy_name,
            settings_payload=settings.raw_settings,
            output_dir=str(strategy.output_dir),
            worker_ref=strategy.worker_ref,
            entity_ids=strategy.entity_ids,
            start_date=strategy.start_date,
            end_date=strategy.end_date,
        )

        context = SliceBasedRuntimeContext.from_strategy_context(
            strategy,
            execution_mode=settings.execution_mode,
            jobs=jobs,
            task_name=f"enum_{strategy.strategy_name}",
            run_name=f"enum_{strategy.strategy_name}",
            performance=SliceBasedRuntimeContext.default_performance(),
            global_data_meta=global_data_meta,
        )
        return EnumeratorRuntime(context=context, status=SliceBasedRuntimeStatus(stage="preprocess"))

    @staticmethod
    def execute_slice_job(context: JobContext) -> Dict[str, Any]:
        payload = dict(context.payload)
        global_data = payload.pop("_global_data", None)
        if not isinstance(global_data, dict):
            raise ValueError("slice_based job 缺少 _global_data")
        worker_payload = SliceBasedWorker.build_payload({**payload, "global_data": global_data})
        return SliceBasedWorker.run(
            JobContext(
                job_id=context.job_id,
                payload=worker_payload,
                task_name=context.task_name,
            )
        )

    @classmethod
    def execute_backtest(
        cls,
        runtime: EnumeratorRuntime,
        *,
        global_data: Dict[str, List[Dict[str, Any]]],
        on_job_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> List[Any]:
        ctx = runtime.context
        engine_jobs = [
            cls._wrap_backtest_job(job, _global_data=global_data)
            for job in ctx.jobs
        ]
        total_units = max(1, len(ctx.jobs))
        finished = 0

        def on_engine_result(report: JobReport, progress: RunProgress) -> None:
            nonlocal finished
            finished += 1
            runtime.status.progress = JobResultHelper.progress_payload(
                total_jobs=total_units,
                finished=finished,
                completed_jobs=finished if report.success else 0,
                failed_jobs=0 if report.success else 1,
                last_job_id=str(report.job_id),
                last_job_status="completed" if report.success else "failed",
            )
            if on_job_progress is not None:
                on_job_progress(runtime.status.progress)

        result = BacktestEngine.slice_based.run(
            engine_jobs,
            cls.execute_slice_job,
            performance=ctx.performance,
            task_name=ctx.task_name,
            callbacks=RunCallbacks(on_result=on_engine_result),
        )
        runtime.status.job_results = list(result.job_results)
        return [
            JobResultHelper.to_job_result(report)
            for report in result.job_results
        ]

    @staticmethod
    def _wrap_backtest_job(job: Dict[str, Any], **payload_extra: Any) -> Dict[str, Any]:
        job_id = str(job.get("job_id") or "").strip()
        if not job_id:
            raise ValueError("slice_based job requires job_id")
        payload = dict(job)
        payload.update(payload_extra)
        return BacktestJob(id=job_id, payload=payload).to_dict()


__all__ = ["SliceBasedJobPipeline"]
