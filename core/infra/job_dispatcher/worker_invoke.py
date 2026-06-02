"""Worker 子进程/线程内执行 execute（运行时卫生）。"""
from __future__ import annotations

import multiprocessing as mp
from typing import Any, Callable


def invoke_execute(execute: Callable[[dict[str, Any]], Any], payload: dict[str, Any]) -> Any:
    """在 worker 内调用 execute；子进程重置 DatabaseManager 默认实例。"""
    if mp.current_process().name != "MainProcess":
        try:
            from core.infra.db import DatabaseManager

            DatabaseManager.reset_default()
        except Exception:
            pass
    return execute(payload)
