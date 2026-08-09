"""data_source 私有 JobPipeline（线程队列）单测。"""
from __future__ import annotations

from concurrent.futures import Future
from typing import Any, List

from core.modules.data_source.core.service.pipeline.job_pipeline import (
    Job,
    JobContext,
    JobPipeline,
    JobPipelineSettings,
    JobReport,
    RunProgress,
)


class _CollectingExecutor:
    def __init__(self, max_workers: int = 2) -> None:
        self._max_workers = max_workers

    @property
    def max_workers(self) -> int:
        return self._max_workers

    def submit(self, context: JobContext) -> Future:
        fut: Future = Future()
        fut.set_result(
            {
                "success": True,
                "value": context.payload.get("n", 0) * 2,
            }
        )
        return fut

    def shutdown(self, *, wait: bool = True) -> None:
        pass


def test_queue_passes_job_context():
    reports: List[JobReport] = []
    contexts: List[JobContext] = []

    def execute(ctx: JobContext) -> dict:
        contexts.append(ctx)
        return {"success": True, "value": ctx.payload["n"] * 2}

    def on_result(report: JobReport, progress: RunProgress) -> None:
        reports.append(report)

    dispatcher = JobPipeline(
        settings=JobPipelineSettings(max_workers=2, prefetch_ahead=1),
        execute=execute,
        on_result=on_result,
        executor=_CollectingExecutor(max_workers=2),
    )
    result = dispatcher.run(
        [Job(job_id=f"j{i}", payload={"n": i}) for i in range(5)],
        run_name="test:queue",
    )

    assert result.total == 5
    assert result.completed == 5
    assert result.failed == 0
    assert result.run_name == "test:queue"
    assert len(reports) == 5
    assert {r.data["value"] for r in reports} == {0, 2, 4, 6, 8}
    assert all(c.run_name == "test:queue" for c in contexts)


def test_thread_executor_integration():
    reports: List[JobReport] = []

    def execute(ctx: JobContext) -> dict:
        return {"success": True, "doubled": ctx.payload["n"] * 2}

    def on_result(report: JobReport, progress: RunProgress) -> None:
        reports.append(report)

    dispatcher = JobPipeline(
        settings=JobPipelineSettings(max_workers=2),
        execute=execute,
        on_result=on_result,
    )
    result = dispatcher.run([Job("a", {"n": 3}), Job("b", {"n": 5})])

    assert result.completed == 2
    assert len(reports) == 2
    assert {r.data["doubled"] for r in reports} == {6, 10}


def test_execute_exception_does_not_call_on_result():
    reports: List[JobReport] = []

    def execute(ctx: JobContext) -> None:
        raise RuntimeError("boom")

    dispatcher = JobPipeline(
        settings=JobPipelineSettings(max_workers=1),
        execute=execute,
        on_result=lambda report, progress: reports.append(report),
    )
    result = dispatcher.run([Job("x", {})])

    assert result.failed == 1
    assert len(reports) == 0
    assert result.failures[0].phase.value == "execute"
