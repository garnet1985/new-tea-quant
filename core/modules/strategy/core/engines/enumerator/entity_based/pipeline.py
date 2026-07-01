"""entity_based 枚举：job 构建 + BacktestEngine 调度管道。"""
from __future__ import annotations

from typing import Any, Callable, ClassVar, Dict, List, Optional, Tuple

from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import BacktestJob, JobContext, JobReport, RunCallbacks, RunProgress
from core.modules.backtest_engine.core.shared.performance import (
    EntityBasedPerformance,
    resolve_entity_based_performance,
)

from ..shared.runtime import EnumeratorRuntime, JobResultHelper
from .worker import EntityBasedWorker


class EntityBasedWorkerContext:
    """entity_based worker 性能基线（非用户 settings）。"""

    RESERVE_CORES: ClassVar[int] = 2
    MAX_PARALLEL_JOBS_CAP: ClassVar[Optional[int]] = None
    MEMORY_BUDGET_MB: ClassVar[str] = "auto"
    MEMORY_FLOOR_MB: ClassVar[str] = "auto"
    ENTITIES_PER_JOB: ClassVar[str] = "auto"
    DISPATCH_PROBE: ClassVar[bool] = True
    ENTITIES_PER_JOB_MIN: ClassVar[int] = 1
    ENTITIES_PER_JOB_MAX: ClassVar[int] = 500
    WORKER_MEMORY_FRACTION: ClassVar[float] = 0.85
    PREFETCH_AHEAD: ClassVar[int] = 1

    _runtime_tune: ClassVar[Dict[str, Any]] = {}

    @classmethod
    def baseline(cls) -> Dict[str, Any]:
        return {
            "reserve_cores": cls.RESERVE_CORES,
            "max_parallel_jobs_cap": cls.MAX_PARALLEL_JOBS_CAP,
            "memory_budget_mb": cls.MEMORY_BUDGET_MB,
            "memory_floor_mb": cls.MEMORY_FLOOR_MB,
            "entities_per_job": cls.ENTITIES_PER_JOB,
            "dispatch_probe": cls.DISPATCH_PROBE,
            "entities_per_job_min": cls.ENTITIES_PER_JOB_MIN,
            "entities_per_job_max": cls.ENTITIES_PER_JOB_MAX,
            "worker_memory_fraction": cls.WORKER_MEMORY_FRACTION,
            "prefetch_ahead": cls.PREFETCH_AHEAD,
        }

    @classmethod
    def apply_runtime_tune(cls, **kwargs: Any) -> None:
        cls._runtime_tune.update(kwargs)

    @classmethod
    def clear_runtime_tune(cls) -> None:
        cls._runtime_tune.clear()

    @classmethod
    def performance(cls) -> Dict[str, Any]:
        merged = cls.baseline()
        if cls._runtime_tune:
            merged = EntityBasedPerformance.from_dict(merged).merge(cls._runtime_tune).to_dict()
        return resolve_entity_based_performance(merged)


class EntityBasedJobPipeline:
    """组装 jobs + execute_fn，交给 BacktestEngine.entity_based。"""

    @staticmethod
    def execute_entity_based_job(context: JobContext) -> Dict[str, Any]:
        payload = dict(context.payload)
        batch_entities = payload.get("jobs")
        if isinstance(batch_entities, list) and batch_entities:
            dispatch_job = EntityBasedJobPipeline._merge_batch(batch_entities, context.job_id)
            global_data = (
                dispatch_job.get("_global_data")
                or payload.get("_global_data")
                or {}
            )
            worker_payload = EntityBasedWorker.build_payload(dispatch_job, global_data)
            return EntityBasedWorker.run(
                JobContext(
                    job_id=context.job_id,
                    payload=worker_payload,
                    task_name=context.task_name,
                )
            )

        global_data = payload.get("_global_data") or {}
        worker_payload = EntityBasedWorker.build_payload(payload, global_data)
        return EntityBasedWorker.run(
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
        total_jobs: int,
        on_job_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> List[Any]:
        ctx = runtime.context
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
            cls.execute_entity_based_job,
            performance=ctx.performance or EntityBasedWorkerContext.performance(),
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
        stock_id = str(job.get("stock_id") or "").strip()
        if not stock_id:
            raise ValueError("entity_based job requires stock_id")
        payload = dict(job)
        payload.update(payload_extra)
        return BacktestJob(id=stock_id, payload=payload).to_dict()

    @staticmethod
    def _merge_batch(entities: List[Dict[str, Any]], batch_job_id: str) -> Dict[str, Any]:
        rows = BacktestJob.batch_payloads(entities)
        base = dict(rows[0])
        stock_ids = [
            str(row.get("stock_id") or "").strip()
            for row in rows
            if str(row.get("stock_id") or "").strip()
        ]
        if not stock_ids:
            raise ValueError("entity_based batch payload must include stock_id")

        merged = {
            key: value
            for key, value in base.items()
            if key not in {"job_id", "stock_id", "stock_ids", "id", "payload"}
        }
        merged["job_id"] = stock_ids[0] if len(stock_ids) == 1 else batch_job_id
        merged["stock_ids"] = stock_ids
        if len(stock_ids) == 1:
            merged["stock_id"] = stock_ids[0]
        merged["_global_data"] = base.get("_global_data")
        return merged

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


__all__ = [
    "EntityBasedJobPipeline",
    "EntityBasedWorkerContext",
]
