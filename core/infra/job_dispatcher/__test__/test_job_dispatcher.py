# JobDispatcher 单元测试
from __future__ import annotations

from concurrent.futures import Future
from typing import Any, Dict, List

from core.infra.job_dispatcher import (
    DispatchConfig,
    JobDispatcher,
    JobReport,
    JobShell,
    StagedJob,
)
from core.infra.job_dispatcher.types import ExecutionBackend
from core.infra.job_dispatcher.executors.pool import ThreadJobExecutor


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


def test_dispatcher_runs_shells_with_hooks():
    reports: List[JobReport] = []

    def on_stage_job(shell: JobShell) -> StagedJob:
        return StagedJob(
            job_id=shell.job_id,
            shell=shell,
            payload={"n": shell.payload["n"]},
        )

    def on_report(report: JobReport) -> None:
        reports.append(report)

    dispatcher = JobDispatcher(
        on_stage_job=on_stage_job,
        on_report=on_report,
        executor=_CollectingExecutor(max_workers=2),
        config=DispatchConfig(prefetch_ahead=1),
    )

    shells = [JobShell(job_id=f"j{i}", payload={"n": i}) for i in range(5)]
    result = dispatcher.run(shells)

    assert result.total == 5
    assert result.completed == 5
    assert result.failed == 0
    assert len(reports) == 5
    assert {r.data["value"] for r in reports} == {0, 2, 4, 6, 8}


def test_thread_executor_integration():
    reports: List[JobReport] = []

    def execute(payload: dict) -> dict:
        return {"success": True, "doubled": payload["n"] * 2}

    def on_stage_job(shell: JobShell) -> StagedJob:
        return StagedJob(job_id=shell.job_id, shell=shell, payload=dict(shell.payload))

    def on_report(report: JobReport) -> None:
        reports.append(report)

    executor = ThreadJobExecutor(max_workers=2, execute=execute)
    dispatcher = JobDispatcher(
        on_stage_job=on_stage_job,
        on_report=on_report,
        executor=executor,
    )
    result = dispatcher.run([JobShell("a", {"n": 3}), JobShell("b", {"n": 5})])

    assert result.completed == 2
    assert len(reports) == 2
    assert reports[0].data["doubled"] in (6, 10)


def _process_execute_double(payload: dict) -> dict:
    """模块级 execute，供 ProcessPoolExecutor pickle。"""
    return {"success": True, "doubled": payload["n"] * 2}


def test_process_executor_integration():
    from core.infra.job_dispatcher.executors.pool import ProcessJobExecutor

    reports: List[JobReport] = []

    def on_stage_job(shell: JobShell) -> StagedJob:
        return StagedJob(job_id=shell.job_id, shell=shell, payload=dict(shell.payload))

    def on_report(report: JobReport) -> None:
        reports.append(report)

    executor = ProcessJobExecutor(
        max_workers=2,
        execute=_process_execute_double,
        start_method="spawn",
    )
    dispatcher = JobDispatcher(
        on_stage_job=on_stage_job,
        on_report=on_report,
        executor=executor,
    )
    result = dispatcher.run(
        [JobShell("a", {"n": 3}), JobShell("b", {"n": 5}), JobShell("c", {"n": 7})]
    )

    assert result.completed == 3
    assert result.failed == 0
    assert len(reports) == 3
    assert {r.data["doubled"] for r in reports} == {6, 10, 14}
