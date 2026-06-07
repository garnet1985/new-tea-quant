"""
ProcessWorker 单元测试（废弃 API + resolve 工具）
"""
from __future__ import annotations

import pytest

from core.infra.worker.multi_process.process_worker import (
    ExecutionMode,
    JobStatus,
    ProcessWorker,
)
from core.infra.worker.multi_process.task_type import TaskType


def test_init_default():
    worker = ProcessWorker(is_verbose=False)
    assert worker.max_workers is None
    assert worker.execution_mode == ExecutionMode.QUEUE
    assert worker.is_verbose is False


def test_init_with_config():
    worker = ProcessWorker(
        max_workers=4,
        execution_mode=ExecutionMode.BATCH,
        is_verbose=True,
    )
    assert worker.max_workers == 4
    assert worker.execution_mode == ExecutionMode.BATCH


def test_resolve_max_workers_manual():
    assert ProcessWorker.resolve_max_workers(8, "TestModule") == 8


def test_run_jobs_raises():
    worker = ProcessWorker(max_workers=2, is_verbose=False)
    with pytest.raises(RuntimeError, match="ProcessWorker.run_jobs 已移除"):
        worker.run_jobs([{"id": "1", "data": {"value": 1}}])


def test_calculate_workers():
    for task_type in (
        TaskType.CPU_INTENSIVE,
        TaskType.IO_INTENSIVE,
        TaskType.MIXED,
    ):
        workers = ProcessWorker.calculate_workers(task_type, reserve_cores=2)
        assert isinstance(workers, int)
        assert workers > 0
