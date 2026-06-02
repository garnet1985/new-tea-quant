# JobDispatcher 单元测试
from __future__ import annotations

from concurrent.futures import Future
from typing import Any, List

import pytest

from core.infra.job_dispatcher import (
    ExecuteMode,
    ExecutionBackend,
    Job,
    JobDispatchSettings,
    JobDispatcher,
    JobFailurePhase,
    JobReport,
    RunProgress,
)
from core.infra.job_dispatcher.executors.pool import ProcessJobExecutor, ThreadJobExecutor


class _CollectingExecutor:
    def __init__(self, max_workers: int = 2) -> None:
        self._max_workers = max_workers

    @property
    def max_workers(self) -> int:
        return self._max_workers

    @property
    def requires_picklable_payload(self) -> bool:
        return False

    def submit(self, job_id: str, payload: dict[str, Any]) -> Future:
        fut: Future = Future()
        fut.set_result({"job_id": job_id, "value": payload.get("n", 0) * 2})
        return fut

    def shutdown(self, *, wait: bool = True, timeout: float | None = None) -> None:
        pass

    def get_stats(self) -> dict[str, Any]:
        return {}


def test_dispatcher_without_to_executable_job():
    reports: List[JobReport] = []
    progresses: List[RunProgress] = []

    def on_result(report: JobReport, progress: RunProgress) -> None:
        reports.append(report)
        progresses.append(progress)

    settings = JobDispatchSettings(
        worker=ExecutionBackend.THREAD,
        max_workers=2,
        prefetch_ahead=1,
    )
    dispatcher = JobDispatcher(
        settings=settings,
        execute=lambda p: {"success": True, "value": p["n"] * 2},
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
    assert progresses[-1].finished == 5
    assert progresses[-1].total == 5


def test_dispatcher_with_to_executable_job():
    reports: List[JobReport] = []

    def to_executable_job(job: Job) -> Job:
        return Job(job_id=job.job_id, payload={"n": job.payload["n"], "staged": True})

    def on_result(report: JobReport, progress: RunProgress) -> None:
        reports.append(report)

    class _StagedExecutor(_CollectingExecutor):
        def submit(self, job_id: str, payload: dict[str, Any]) -> Future:
            fut: Future = Future()
            fut.set_result({"success": True, "staged": payload.get("staged"), "n": payload["n"]})
            return fut

    dispatcher = JobDispatcher(
        settings=JobDispatchSettings(worker=ExecutionBackend.THREAD, max_workers=2),
        execute=lambda p: {"success": True, "staged": p.get("staged"), "n": p["n"]},
        to_executable_job=to_executable_job,
        on_result=on_result,
        executor=_StagedExecutor(max_workers=2),
    )
    result = dispatcher.run([Job("j1", {"n": 3})])

    assert result.completed == 1
    assert reports[0].data["staged"] is True


def test_prepare_failure_recorded():
    def to_executable_job(job: Job) -> Job:
        if job.job_id == "bad":
            raise RuntimeError("stage boom")
        return job

    def on_result(report: JobReport, progress: RunProgress) -> None:
        pass

    dispatcher = JobDispatcher(
        settings=JobDispatchSettings(worker=ExecutionBackend.THREAD, max_workers=1),
        execute=lambda p: p,
        to_executable_job=to_executable_job,
        on_result=on_result,
        executor=_CollectingExecutor(max_workers=1),
    )
    result = dispatcher.run([Job("bad", {}), Job("ok", {"n": 1})])

    assert result.total == 2
    assert result.failed == 1
    assert result.completed == 1
    assert result.failures[0].phase == JobFailurePhase.TO_EXECUTABLE


def test_thread_executor_integration():
    reports: List[JobReport] = []

    def execute(payload: dict) -> dict:
        return {"success": True, "doubled": payload["n"] * 2}

    def on_result(report: JobReport, progress: RunProgress) -> None:
        reports.append(report)

    settings = JobDispatchSettings(worker=ExecutionBackend.THREAD, max_workers=2)
    dispatcher = JobDispatcher(
        settings=settings,
        execute=execute,
        on_result=on_result,
    )
    result = dispatcher.run([Job("a", {"n": 3}), Job("b", {"n": 5})])

    assert result.completed == 2
    assert len(reports) == 2
    assert {r.data["doubled"] for r in reports} == {6, 10}


def _process_execute_double(payload: dict) -> dict:
    return {"success": True, "doubled": payload["n"] * 2}


def test_process_executor_integration():
    reports: List[JobReport] = []

    def on_result(report: JobReport, progress: RunProgress) -> None:
        reports.append(report)

    settings = JobDispatchSettings(
        worker=ExecutionBackend.PROCESS,
        max_workers=2,
        start_method="spawn",
    )
    dispatcher = JobDispatcher(
        settings=settings,
        execute=_process_execute_double,
        on_result=on_result,
    )
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

    settings = JobDispatchSettings(
        worker=ExecutionBackend.THREAD,
        execute_mode=ExecuteMode.BATCH,
        max_workers=2,
        batch_size=2,
    )
    dispatcher = JobDispatcher(
        settings=settings,
        execute=lambda p: {"success": True, "n": p["n"]},
        on_result=on_result,
        executor=_CollectingExecutor(max_workers=2),
    )
    result = dispatcher.run([Job(f"j{i}", {"n": i}) for i in range(4)])

    assert result.completed == 4
    assert len(reports) == 4


def test_elastic_mode_not_implemented():
    dispatcher = JobDispatcher(
        settings=JobDispatchSettings(execute_mode=ExecuteMode.ELASTIC),
        execute=lambda p: p,
        on_result=lambda r, p: None,
        executor=_CollectingExecutor(max_workers=1),
    )
    with pytest.raises(NotImplementedError):
        dispatcher.run([Job("x", {})])
