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
from core.modules.strategy.core.engines.enumerator.entity_based.services.job_builder import JobBuilder
from core.modules.strategy.core.engines.enumerator.shared.services.recorder import EnumeratorOutputRecorder

from .runtime_context.context import EntityBasedRuntimeContext

logger = logging.getLogger(__name__)


class EntityBasedJobPipeline:
    """entity_based 枚举完整流程。"""

    @classmethod
    def _load_result_cache_by_fingerprints(cls, context: EntityBasedRuntimeContext, cache: Dict[str, Any] = None) -> bool:
        """执行回测。"""
        settings_fp, env_fp = fingerprint.build_fingerprint(context)
        cache = dm.load_cache(settings_fp, env_fp)
        return cache

    @classmethod
    def _preprocess(cls, strategy_info: EnabledStrategyInfo, global_data_cache: Dict[str, Any] = None):
        """预处理逻辑步骤（具体实施下沉到子context）。"""

        # Step 1: Init Context（调用子context.init）
        context = EntityBasedRuntimeContext.init(strategy_info, global_data_cache)

        # Step 2: Check Cache（通过fingerprint查找）
        cached_result = cls._load_result_cache_by_fingerprints(context, global_data_cache)
        if cached_result:
            return cached_result, None, None, None

        # Step 3: Prepare for Execution
        recorder = EnumeratorOutputRecorder.from_context(context)
        jobs = JobBuilder.build_jobs(context)

        # Step 4: Save Metadata（只保存元信息，不保存完整jobs）
        recorder.save_execution_metadata(
            fingerprint={"hash": context.info.fingerprint_hash},
            total_jobs=len(jobs),
            jobs_sample=[jobs[0].to_dict()] if jobs else [],  # 只保存第一个job作为sample
            settings_diff={},  # TODO: 计算settings_diff
        )

        return None, jobs, context, recorder



    @classmethod
    def execute(cls, context: EntityBasedRuntimeContext, jobs: List[BacktestJob]) -> List[JobReport]:
        """执行回测。"""
        return cls.execute_backtest(context, jobs)

    @classmethod
    def _postprocess(cls, context, results, recorder) -> Dict[str, Any]:
        """后处理。"""
        # TODO: 实现后处理逻辑
        # - 计算report
        # - recorder.save_final_results(report)
        pass

    @classmethod
    def run(cls, strategy_info: EnabledStrategyInfo, cache: Dict[str, Any] = None) -> Dict[str, Any]:

        cached_result, jobs, context, recorder = cls._preprocess(strategy_info, cache)

        if cached_result:
            # TODO: 从缓存构建结果
            return cached_result

        results = cls.execute(context, jobs)

        cls._postprocess(context, results, recorder)



        # recorder.save_preprocess_intermediate(
        #     fingerprint={"hash": ctx.fingerprint_hash},
        #     jobs=ctx.jobs,
        #     settings_diff=ctx.settings_diff,
        # )



        # runtime = cls.build_runtime(strategy)
        # ctx = runtime.context

        # recorder = EnumeratorOutputRecorder(
        #     output_dir=strategy.output_dir,
        #     strategy_name=strategy.strategy_name,
        #     version_id=strategy.version_id,
        #     version_dir_name=strategy.version_dir_name,
        # )
        # recorder.save_preprocess_intermediate(
        #     fingerprint={"hash": ctx.fingerprint_hash},
        #     jobs=ctx.jobs,
        #     settings_diff=ctx.settings_diff,
        # )

        # global_data, global_meta = GlobalDataPreloader.preload(
        #     settings=strategy.effective_settings.raw_settings,
        #     start_date=strategy.start_date,
        #     end_date=strategy.end_date,
        #     entity_ids=strategy.entity_ids,
        # )
        # ctx.global_data_meta.update(global_meta)

        # runtime.status.stage = "execute"
        # job_results = cls.execute_backtest(runtime, global_data=global_data)

        # for job_result in job_results:
        #     for stock_id, opportunities in iter_opportunities_from_job_result(job_result):
        #         if stock_id and opportunities:
        #             recorder.save_stock_opportunities(stock_id, opportunities)

        # report_template = EnumeratorReportStatistics.compute_from_dir(
        #     strategy.output_dir,
        #     total_stocks_hint=len(strategy.entity_ids),
        # )

        # runtime.status.stage = "postprocess"
        # metadata = {
        #     "strategy_name": strategy.strategy_name,
        #     "version_id": strategy.version_id,
        #     "version_dir_name": strategy.version_dir_name,
        #     "fingerprint_hash": ctx.fingerprint_hash,
        #     "start_date": strategy.start_date,
        #     "end_date": strategy.end_date,
        #     "total_stocks": len(strategy.entity_ids),
        #     "execution_mode": ctx.execution_mode,
        #     "status": "completed",
        # }
        # recorder.save_postprocess_intermediate(
        #     metadata=metadata,
        #     report=EnumeratorReportStatistics.to_bff_payload(
        #         report_template,
        #         include_stock_rows=False,
        #     ),
        # )

        # logger.info(
        #     "Enumeration completed: opportunities=%d, trigger_stocks=%d",
        #     report_template.total_opportunities,
        #     report_template.trigger_stocks,
        # )

        # return {
        #     "success": True,
        #     "total_opportunities": report_template.total_opportunities,
        #     "trigger_stocks": report_template.trigger_stocks,
        #     "fingerprint_hash": ctx.fingerprint_hash,
        #     "execution_mode": ctx.execution_mode,
        # }

    # @classmethod
    # def build_runtime(
    #     cls,
    #     strategy: StrategyContext,
    #     *,
    #     global_data_meta: Optional[Dict[str, Any]] = None,
    # ) -> EnumeratorRuntime:
    #     settings = strategy.effective_settings

    #     if not settings.is_entity_based:
    #         raise ValueError(
    #             f"EntityBasedJobPipeline 期望 entity_based，实际 {settings.execution_mode!r}"
    #         )

    #     jobs = EntityBasedJobs.build(
    #         strategy_name=strategy.strategy_name,
    #         settings_payload=settings.raw_settings,
    #         output_dir=str(strategy.output_dir),
    #         worker_ref=strategy.worker_ref,
    #         stock_ids=strategy.entity_ids,
    #         start_date=strategy.start_date,
    #         end_date=strategy.end_date,
    #     )

    #     context = EntityBasedRuntimeContext.from_strategy_context(
    #         strategy,
    #         execution_mode=settings.execution_mode,
    #         jobs=jobs,
    #         task_name=f"enum_{strategy.strategy_name}",
    #         run_name=f"enum_{strategy.strategy_name}",
    #         performance=EntityBasedRuntimeContext.default_performance(),
    #         global_data_meta=global_data_meta,
    #     )
    #     return EnumeratorRuntime(context=context, status=EntityBasedRuntimeStatus(stage="preprocess"))

    # @classmethod
    # def execute_backtest(
    #     cls,
    #     runtime: EnumeratorRuntime,
    #     *,
    #     global_data: Dict[str, List[Dict[str, Any]]],
    #     on_job_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    # ) -> List[Any]:
    #     ctx = runtime.context
    #     total_jobs = cls._entity_count_from_jobs(ctx.jobs)
    #     engine_jobs = [
    #         cls._wrap_backtest_job(job, _global_data=global_data)
    #         for job in ctx.jobs
    #     ]

    #     stock_finished = 0
    #     stock_ok = 0
    #     stock_fail = 0
    #     progress_meta = {"last_job_id": "", "last_job_status": ""}

    #     def on_engine_result(report: JobReport, progress: RunProgress) -> None:
    #         nonlocal stock_finished, stock_ok, stock_fail
    #         progress_meta["last_job_id"] = report.job_id
    #         progress_meta["last_job_status"] = "completed" if report.success else "failed"
    #         units, ok_u, fail_u = cls._progress_units_from_report(report)
    #         stock_finished += units
    #         stock_ok += ok_u
    #         stock_fail += fail_u
    #         progress_payload = JobResultHelper.progress_payload(
    #             total_jobs=total_jobs,
    #             finished=stock_finished,
    #             completed_jobs=stock_ok,
    #             failed_jobs=stock_fail,
    #             last_job_id=progress_meta["last_job_id"],
    #             last_job_status=progress_meta["last_job_status"],
    #         )
    #         runtime.status.progress = progress_payload
    #         if on_job_progress is not None:
    #             on_job_progress(progress_payload)

    #     result = BacktestEngine.entity_based.run(
    #         engine_jobs,
    #         EntityBasedWorker.execute,
    #         performance=ctx.performance,
    #         task_name=ctx.task_name,
    #         callbacks=RunCallbacks(
    #             on_job_init=EntityBasedWorker.on_init,
    #             on_job_release=EntityBasedWorker.on_release,
    #             on_result=on_engine_result,
    #         ),
    #     )
    #     runtime.status.job_results = list(result.job_results)
    #     return [
    #         JobResultHelper.to_job_result(report)
    #         for report in result.job_results
    #     ]

    # @staticmethod
    # def _entity_count_from_jobs(jobs: List[Dict[str, Any]]) -> int:
    #     total = 0
    #     for job in jobs:
    #         stock_ids = job.get("stock_ids")
    #         if isinstance(stock_ids, list) and stock_ids:
    #             total += len(stock_ids)
    #         elif job.get("stock_id"):
    #             total += 1
    #     return max(total, len(jobs))

    # @staticmethod
    # def _wrap_backtest_job(job: Dict[str, Any], **payload_extra: Any) -> Dict[str, Any]:
    #     entity_id = str(job.get("entity_id") or "").strip()
    #     if not entity_id:
    #         raise ValueError("entity_based job 缺少 entity_id")
    #     payload = dict(job)
    #     payload.update(payload_extra)
    #     return BacktestJob(id=entity_id, payload=payload).to_dict()

    # @staticmethod
    # def _progress_units_from_report(report: JobReport) -> Tuple[int, int, int]:
    #     data = report.data
    #     if not isinstance(data, dict):
    #         ok = 1 if report.success else 0
    #         return ok + (1 - ok), ok, 1 - ok
    #     if data.get("bulk") and isinstance(data.get("stock_results"), list):
    #         ok = fail = 0
    #         for row in data["stock_results"]:
    #             if isinstance(row, dict) and row.get("success"):
    #                 ok += 1
    #             else:
    #                 fail += 1
    #         return ok + fail, ok, fail
    #     ok = 1 if data.get("success") else 0
    #     fail = 0 if ok else 1
    #     return ok + fail, ok, fail


__all__ = ["EntityBasedJobPipeline"]
