"""slice_based 枚举：job 构建 + BacktestEngine 调度管道。"""
from __future__ import annotations

from typing import Any, Callable, ClassVar, Dict, List, Optional

from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import BacktestJob, JobContext, JobReport, RunCallbacks, RunProgress
from core.modules.backtest_engine.core.shared.performance import resolve_slice_based_performance

from ..shared.runtime import EnumeratorRuntime, JobResultHelper
from .worker import SliceBasedWorker


class SliceBasedWorkerContext:
    """slice_based 性能基线。"""

    READER_WORKERS: ClassVar[str] = "auto"
    QUEUE_DEPTH: ClassVar[str] = "auto"
    PREFETCH_ENABLED: ClassVar[bool] = True
    SLICE_OPEN_DAYS: ClassVar[str] = "auto"

    _runtime_tune: ClassVar[Dict[str, Any]] = {}

    @classmethod
    def baseline(cls) -> Dict[str, Any]:
        return {
            "reader_workers": cls.READER_WORKERS,
            "queue_depth": cls.QUEUE_DEPTH,
            "prefetch_enabled": cls.PREFETCH_ENABLED,
            "slice_open_days": cls.SLICE_OPEN_DAYS,
            # 探针 / 分片 / reader 调度由 BacktestEngine 负责；Strategy 只跑 compute
            "slice_probe": False,
        }

    @classmethod
    def apply_runtime_tune(cls, **kwargs: Any) -> None:
        cls._runtime_tune.update(kwargs)

    @classmethod
    def clear_runtime_tune(cls) -> None:
        cls._runtime_tune.clear()

    @classmethod
    def performance(cls) -> Dict[str, Any]:
        merged = dict(cls.baseline())
        merged.update(cls._runtime_tune)
        return resolve_slice_based_performance(merged)


class SliceBasedJobPipeline:
    """组装 bulk job + execute_fn，交给 BacktestEngine.slice_based。"""

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
    def run(
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
            performance=ctx.performance or SliceBasedWorkerContext.performance(),
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


__all__ = [
    "SliceBasedJobPipeline",
    "SliceBasedWorkerContext",
]
