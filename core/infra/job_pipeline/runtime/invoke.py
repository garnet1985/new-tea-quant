"""Worker 子进程/线程内执行 execute（运行时卫生）。"""
from __future__ import annotations

import multiprocessing as mp
from typing import Any, Callable

from core.infra.job_pipeline.types import JobContext


def invoke_execute(execute: Callable[[JobContext], Any], context: JobContext) -> Any:
    if mp.current_process().name != "MainProcess":
        try:
            from core.infra.db import DatabaseManager

            DatabaseManager.reset_default()
        except Exception:
            pass
    return execute(context)
