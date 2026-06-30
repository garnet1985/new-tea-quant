"""Timeline execute pipeline: plan → monitor → process-pool execution."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.modules.backtest_engine.core.shared.context import ExecutionContext
from core.modules.backtest_engine.core.shared.machine_info import MachineInfo
from core.modules.backtest_engine.core.shared.types import JobReport, RunProgress
from core.modules.backtest_engine.core.timeline_based.executor import TimelineExecutor
from core.modules.backtest_engine.core.timeline_based.executor_duckdb import (
    TimelineExecutorDuckDB,
)
from core.modules.backtest_engine.core.timeline_based.monitor import (
    MonitorPlanSnapshot,
    TimelineJobSample,
    TimelineMonitorConfig,
    TimelineRunMonitor,
)
from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.backtest_engine.core.timeline_based.planner import (
    DispatchPlan,
    JobBatch,
    TimelinePlanner,
)

logger = logging.getLogger(__name__)


class TimelineExecutePipeline:
    """End-to-end timeline backtest: plan → monitor → execute."""

    ExecuteFn = TimelineExecutor.ExecuteFn
    OnResultHook = TimelineExecutor.OnResultHook
    OnReleaseHook = TimelineExecutor.OnReleaseHook

    @dataclass(frozen=True)
    class Result:
        plan: DispatchPlan
        batches: List[JobBatch]
        monitor_config: TimelineMonitorConfig
        execution: TimelineExecutor.ExecutionResult
        monitor_stats: Any = None

    def __init__(self, *, log_label: str = "timeline") -> None:
        self._log_label = log_label

    def run(
        self,
        jobs: List[Dict[str, Any]],
        performance: Dict[str, Any],
        *,
        execute_fn: TimelineExecutor.ExecuteFn,
        task_name: str = "",
        on_result: Optional[TimelineExecutor.OnResultHook] = None,
        on_release: Optional[TimelineExecutor.OnReleaseHook] = None,
    ) -> TimelineExecutePipeline.Result:
        if jobs:
            BacktestJob.validate_many(jobs)
        plan, batches, monitor_config = self._plan(jobs, performance, execute_fn)
        capacity = MachineInfo.get_capacity(performance)
        available_memory_mb = MachineInfo.worker_pool_budget_mb(capacity)
        monitor = TimelineRunMonitor(
            MonitorPlanSnapshot(
                entities_per_job=plan.entities_per_job,
                max_workers=plan.max_workers,
                prefetch_ahead=plan.prefetch_ahead,
                worker_job_budget_mb=plan.worker_job_budget_mb,
            ),
            monitor_config,
            available_memory_mb=available_memory_mb,
            cpu_workers_cap=MachineInfo.get_available_workers(capacity),
        )
        context = ExecutionContext.create(
            run_name=task_name or self._log_label,
            total_jobs=len(batches),
            executor="",
            performance=performance,
        )

        batch_entities = {batch.batch_id: batch.entities_count for batch in batches}

        def monitored_on_result(report: JobReport, progress: RunProgress) -> None:
            monitor.record(
                _job_sample_from_report(report, batch_entities),
            )
            if on_result is not None:
                on_result(report, progress)

        execution = TimelineExecutorDuckDB.execute(
            plan,
            batches,
            context,
            execute_fn,
            on_result=monitored_on_result,
            on_release=on_release,
            log_label=self._log_label,
            get_admission_limit=lambda: monitor.admission_limit,
            duckdb_process_pool_scope=str(
                performance.get("duckdb_process_pool_scope", "auto")
            ),
            duckdb_resume_main_after_pool=bool(
                performance.get("duckdb_resume_main_after_pool", True)
            ),
        )
        monitor.flush()

        return TimelineExecutePipeline.Result(
            plan=plan,
            batches=batches,
            monitor_config=monitor_config,
            execution=execution,
            monitor_stats=monitor.stats,
        )

    def _plan(
        self,
        jobs: List[Dict[str, Any]],
        performance: Dict[str, Any],
        execute_fn: TimelineExecutor.ExecuteFn,
    ) -> tuple[DispatchPlan, List[JobBatch], TimelineMonitorConfig]:
        return TimelinePlanner.plan_jobs(
            jobs,
            performance,
            execute_fn=execute_fn,
            log_label=self._log_label,
        )


def _job_sample_from_report(
    report: JobReport,
    batch_entities: Dict[str, int],
) -> TimelineJobSample:
    data = report.data if isinstance(report.data, dict) else {}
    entities_count = int(
        data.get("entities_count") or batch_entities.get(report.job_id, 0)
    )
    peak_rss = data.get("peak_rss_mb")
    return TimelineJobSample(
        job_id=report.job_id,
        entities_count=entities_count,
        wall_sec=float(data.get("wall_sec") or 0.0),
        peak_rss_mb=float(peak_rss) if peak_rss is not None else None,
        success=report.success,
    )


__all__ = ["TimelineExecutePipeline"]
