#!/usr/bin/env python3
"""Job 树 RSS 采样（orchestrator + reader + compute 子进程）。"""

from __future__ import annotations

import os
from typing import Iterable, Optional, Sequence


def process_rss_mb(pid: int) -> float:
    try:
        import psutil

        return float(psutil.Process(pid).memory_info().rss) / (1024.0 * 1024.0)
    except Exception:
        return 0.0


def job_tree_rss_mb(*, child_pids: Sequence[int]) -> float:
    """当前进程 + 指定子进程 RSS 合计。"""
    total = process_rss_mb(os.getpid())
    for pid in child_pids:
        if pid > 0:
            total += process_rss_mb(pid)
    return total


def available_system_memory_mb() -> Optional[float]:
    try:
        import psutil

        return float(psutil.virtual_memory().available) / (1024.0 * 1024.0)
    except Exception:
        return None


def collect_child_pids(procs: Iterable[object]) -> tuple[int, ...]:
    out = []
    for proc in procs:
        pid = getattr(proc, "pid", None)
        if pid is not None and int(pid) > 0:
            out.append(int(pid))
    return tuple(out)


__all__ = [
    "available_system_memory_mb",
    "collect_child_pids",
    "job_tree_rss_mb",
    "process_rss_mb",
]
