"""entity_based 主执行流程 — preprocess → BacktestEngine → postprocess。

子进程逻辑见 ``worker.py``（``EntityBasedWorker``）。
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import BacktestJob, JobReport, RunCallbacks, RunProgress
from core.modules.strategy.core.context.strategy_context import StrategyContext
from core.modules.strategy.core.services.data.entity_data import GlobalDataPreloader
from core.modules.strategy.core.services.data.output_recorder import EnumeratorOutputRecorder

from ..shared.opportunities import iter_opportunities_from_job_result
from ..shared.report.statistics import EnumeratorReportStatistics
from ..shared.runtime import EnumeratorRuntime, JobResultHelper
from .context.runtime import EntityBasedRuntimeContext
from .context.status import EntityBasedRuntimeStatus
from .resolver.jobs import EntityBasedJobs
from .worker import EntityBasedWorker

logger = logging.getLogger(__name__)


class EntityBasedJobPipeline:
    """entity_based 枚举完整流程。"""

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

        if not settings.is_entity_based:
            raise ValueError(
                f"EntityBasedJobPipeline 期望 entity_based，实际 {settings.execution_mode!r}"
            )

        jobs = EntityBasedJobs.build(
            strategy_name=strategy.strategy_name,
            settings_payload=settings.raw_settings,
            output_dir=str(strategy.output_dir),
            worker_ref=strategy.worker_ref,
            stock_ids=strategy.entity_ids,
            start_date=strategy.start_date,
            end_date=strategy.end_date,
        )

        context = EntityBasedRuntimeContext.from_strategy_context(
            strategy,
            execution_mode=settings.execution_mode,
            jobs=jobs,
            task_name=f"enum_{strategy.strategy_name}",
            run_name=f"enum_{strategy.strategy_name}",
            performance=EntityBasedRuntimeContext.default_performance(),
            global_data_meta=global_data_meta,
        )
        return EnumeratorRuntime(context=context, status=EntityBasedRuntimeStatus(stage="preprocess"))

    @classmethod
    def execute_backtest(
        cls,
        runtime: EnumeratorRuntime,
        *,
        global_data: Dict[str, List[Dict[str, Any]]],
        on_job_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> List[Any]:
        ctx = runtime.context
        total_jobs = cls._entity_count_from_jobs(ctx.jobs)
        engine_jobs = [
            cls._wrap_backtest_job(job, _global_data=global_data)
            for job in ctx.jobs
        ]

        stock_finished = 0
        stock_ok = 0
        stock_fail = 0
        progress_meta = {"last_job_id": "", "last_job_status": ""}

        def on_engine_result(report: JobReport, progress: RunProgress) -> None:
            nonlocal stock_finished, stock_ok, stock_fail
            progress_meta["last_job_id"] = report.job_id
            progress_meta["last_job_status"] = "completed" if report.success else "failed"
            units, ok_u, fail_u = cls._progress_units_from_report(report)
            stock_finished += units
            stock_ok += ok_u
            stock_fail += fail_u
            progress_payload = JobResultHelper.progress_payload(
                total_jobs=total_jobs,
                finished=stock_finished,
                completed_jobs=stock_ok,
                failed_jobs=stock_fail,
                last_job_id=progress_meta["last_job_id"],
                last_job_status=progress_meta["last_job_status"],
            )
            runtime.status.progress = progress_payload
            if on_job_progress is not None:
                on_job_progress(progress_payload)

        result = BacktestEngine.entity_based.run(
            engine_jobs,
            EntityBasedWorker.execute,
            performance=ctx.performance,
            task_name=ctx.task_name,
            callbacks=RunCallbacks(
                on_job_init=EntityBasedWorker.on_init,
                on_job_release=EntityBasedWorker.on_release,
                on_result=on_engine_result,
            ),
        )
        runtime.status.job_results = list(result.job_results)
        return [
            JobResultHelper.to_job_result(report)
            for report in result.job_results
        ]

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
    def _wrap_backtest_job(job: Dict[str, Any], **payload_extra: Any) -> Dict[str, Any]:
        entity_id = str(job.get("entity_id") or "").strip()
        if not entity_id:
            raise ValueError("entity_based job 缺少 entity_id")
        payload = dict(job)
        payload.update(payload_extra)
        return BacktestJob(id=entity_id, payload=payload).to_dict()

    @staticmethod
    def _progress_units_from_report(report: JobReport) -> Tuple[int, int, int]:
        data = report.data
        if not isinstance(data, dict):
            ok = 1 if report.success else 0
            return ok + (1 - ok), ok, 1 - ok
        if data.get("bulk") and isinstance(data.get("stock_results"), list):
            ok = fail = 0
            for row in data["stock_results"]:
                if isinstance(row, dict) and row.get("success"):
                    ok += 1
                else:
                    fail += 1
            return ok + fail, ok, fail
        ok = 1 if data.get("success") else 0
        fail = 0 if ok else 1
        return ok + fail, ok, fail


__all__ = ["EntityBasedJobPipeline"]
