# JobPipeline 单元测试
from __future__ import annotations

from concurrent.futures import Future
from contextlib import contextmanager
from typing import Any, List
from unittest.mock import patch

import pytest

from core.infra.job_pipeline import (
    ExecuteMode,
    ExecutionBackend,
    Job,
    JobContext,
    JobPipelineSettings,
    JobPipeline,
    JobReport,
    RunProgress,
)


class _CollectingExecutor:
    def __init__(self, max_workers: int = 2) -> None:
        self._max_workers = max_workers

    @property
    def max_workers(self) -> int:
        return self._max_workers

    @property
    def requires_picklable_payload(self) -> bool:
        return False

    def submit(self, context: JobContext) -> Future:
        fut: Future = Future()
        fut.set_result(
            {
                "job_id": context.job_id,
                "value": context.payload.get("n", 0) * 2,
                "run_name": context.run_name,
            }
        )
        return fut

    def shutdown(self, *, wait: bool = True, timeout: float | None = None) -> None:
        pass

    def get_stats(self) -> dict[str, Any]:
        return {}


def test_dispatcher_queue_passes_job_context():
    reports: List[JobReport] = []
    contexts: List[JobContext] = []

    def execute(ctx: JobContext) -> dict:
        contexts.append(ctx)
        return {"success": True, "value": ctx.payload["n"] * 2}

    def on_result(report: JobReport, progress: RunProgress) -> None:
        reports.append(report)

    settings = JobPipelineSettings(
        worker=ExecutionBackend.THREAD,
        max_workers=2,
        prefetch_ahead=1,
    )
    dispatcher = JobPipeline(
        settings=settings,
        execute=execute,
        on_result=on_result,
        executor=_CollectingExecutor(max_workers=2),
    )

    jobs = [Job(job_id=f"j{i}", payload={"n": i}) for i in range(5)]
    result = dispatcher.run(jobs, run_name="test:queue")

    assert result.total == 5
    assert result.completed == 5
    assert result.failed == 0
    assert result.run_name == "test:queue"
    assert len(reports) == 5
    assert {r.data["value"] for r in reports} == {0, 2, 4, 6, 8}
    assert all(c.run_name == "test:queue" for c in contexts)
    assert all(c.job_id == c.payload["_job_id"] for c in contexts)


def test_thread_executor_integration():
    reports: List[JobReport] = []

    def execute(ctx: JobContext) -> dict:
        return {"success": True, "doubled": ctx.payload["n"] * 2}

    def on_result(report: JobReport, progress: RunProgress) -> None:
        reports.append(report)

    settings = JobPipelineSettings(worker=ExecutionBackend.THREAD, max_workers=2)
    dispatcher = JobPipeline(
        settings=settings,
        execute=execute,
        on_result=on_result,
    )
    result = dispatcher.run([Job("a", {"n": 3}), Job("b", {"n": 5})])

    assert result.completed == 2
    assert len(reports) == 2
    assert {r.data["doubled"] for r in reports} == {6, 10}


def _process_execute_double(ctx: JobContext) -> dict:
    return {"success": True, "doubled": ctx.payload["n"] * 2}


@contextmanager
def _noop_duckdb_scope(*_args, **_kwargs):
    yield None


def test_process_executor_integration():
    reports: List[JobReport] = []

    def on_result(report: JobReport, progress: RunProgress) -> None:
        reports.append(report)

    settings = JobPipelineSettings(
        worker=ExecutionBackend.PROCESS,
        max_workers=2,
        start_method="spawn",
    )
    dispatcher = JobPipeline(
        settings=settings,
        execute=_process_execute_double,
        on_result=on_result,
    )
    with patch(
        "core.infra.job_pipeline.pipeline.runner.maybe_duckdb_worker_pool_scope",
        _noop_duckdb_scope,
    ):
        result = dispatcher.run(
            [Job("a", {"n": 3}), Job("b", {"n": 5}), Job("c", {"n": 7})]
        )

    assert result.completed == 3
    assert result.failed == 0
    assert {r.data["doubled"] for r in reports} == {6, 10, 14}


def test_batch_mode():
    reports: List[JobReport] = []

    def on_result(report: JobReport, progress: RunProgress) -> None:
        reports.append(report)

    settings = JobPipelineSettings(
        worker=ExecutionBackend.THREAD,
        execute_mode=ExecuteMode.BATCH,
        max_workers=2,
        batch_size=2,
    )
    dispatcher = JobPipeline(
        settings=settings,
        execute=lambda ctx: {"success": True, "n": ctx.payload["n"]},
        on_result=on_result,
        executor=_CollectingExecutor(max_workers=2),
    )
    result = dispatcher.run([Job(f"j{i}", {"n": i}) for i in range(4)])

    assert result.completed == 4
    assert len(reports) == 4


def test_execute_exception_does_not_call_on_result():
    reports: List[JobReport] = []

    def execute(ctx: JobContext) -> None:
        raise RuntimeError("boom")

    dispatcher = JobPipeline(
        settings=JobPipelineSettings(worker=ExecutionBackend.THREAD, max_workers=1),
        execute=execute,
        on_result=lambda report, progress: reports.append(report),
    )
    result = dispatcher.run([Job("x", {})])

    assert result.failed == 1
    assert len(reports) == 0
    assert result.failures[0].phase.value == "execute"


def test_elastic_mode_not_implemented():
    dispatcher = JobPipeline(
        settings=JobPipelineSettings(execute_mode=ExecuteMode.ELASTIC),
        execute=lambda ctx: ctx,
        on_result=lambda r, p: None,
        executor=_CollectingExecutor(max_workers=1),
    )
    with pytest.raises(NotImplementedError):
        dispatcher.run([Job("x", {})])
