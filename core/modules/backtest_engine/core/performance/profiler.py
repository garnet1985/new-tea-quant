"""Backtest Engine 运行时性能采集（与 performance.py 调度配置分离）。"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

ENGINE_PERF_KEY = "engine_perf"
ENUM_PERF_KEY = "enum_perf"


@dataclass
class WorkerTaskPerf:
    """单 task 在 worker 内的分阶段墙钟（秒）。"""

    init_sec: float = 0.0
    execute_sec: float = 0.0
    complete_sec: float = 0.0
    wall_sec: float = 0.0
    peak_rss_mb: float = 0.0
    worker_pid: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "init_sec": self.init_sec,
            "execute_sec": self.execute_sec,
            "complete_sec": self.complete_sec,
            "wall_sec": self.wall_sec,
            "peak_rss_mb": self.peak_rss_mb,
            "worker_pid": self.worker_pid,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "WorkerTaskPerf":
        data = raw or {}
        return cls(
            init_sec=float(data.get("init_sec") or 0.0),
            execute_sec=float(data.get("execute_sec") or 0.0),
            complete_sec=float(data.get("complete_sec") or 0.0),
            wall_sec=float(data.get("wall_sec") or 0.0),
            peak_rss_mb=float(data.get("peak_rss_mb") or 0.0),
            worker_pid=int(data.get("worker_pid") or 0),
        )


class WorkerTaskProfiler:
    """Worker 子进程 task 生命周期性能采集（init → execute → complete）。"""

    def __init__(self) -> None:
        import os

        self._worker_pid = os.getpid()
        self._wall_t0 = time.perf_counter()
        self._rss_before_mb = self._process_rss_mb()
        self.init_sec = 0.0
        self.execute_sec = 0.0
        self.complete_sec = 0.0

    def run_init(self, callback: Optional[Callable[[Any], Any]], job_context: Any) -> None:
        if callback is None:
            return
        t0 = time.perf_counter()
        job_context.init = callback(job_context)
        self.init_sec = time.perf_counter() - t0

    def run_execute(
        self,
        execute_fn: Callable[[Any], Any],
        job_context: Any,
    ) -> Tuple[Any, Optional[Exception]]:
        t0 = time.perf_counter()
        try:
            raw = execute_fn(job_context)
            self.execute_sec = time.perf_counter() - t0
            return raw, None
        except Exception as exc:
            self.execute_sec = time.perf_counter() - t0
            return None, exc

    def run_complete(self, callback: Optional[Callable[[Any], Any]], job_context: Any) -> Any:
        if callback is None:
            return None
        t0 = time.perf_counter()
        extra = callback(job_context)
        self.complete_sec = time.perf_counter() - t0
        return extra

    def attach(self, out: Dict[str, Any], *, enum_perf: Any = None) -> Dict[str, Any]:
        wall_sec = time.perf_counter() - self._wall_t0
        rss_after_mb = self._process_rss_mb()
        peak_rss_mb = max(self._rss_before_mb, rss_after_mb)
        payload = dict(out)
        payload["wall_sec"] = wall_sec
        payload["peak_rss_mb"] = peak_rss_mb
        payload[ENGINE_PERF_KEY] = WorkerTaskPerf(
            init_sec=self.init_sec,
            execute_sec=self.execute_sec,
            complete_sec=self.complete_sec,
            wall_sec=wall_sec,
            peak_rss_mb=peak_rss_mb,
            worker_pid=self._worker_pid,
        ).to_dict()
        if isinstance(enum_perf, dict):
            payload[ENUM_PERF_KEY] = dict(enum_perf)
        return payload

    @staticmethod
    def _process_rss_mb() -> float:
        try:
            import os

            import psutil

            return float(psutil.Process(os.getpid()).memory_info().rss) / (
                1024.0 * 1024.0
            )
        except Exception:
            return 0.0


__all__ = [
    "ENGINE_PERF_KEY",
    "ENUM_PERF_KEY",
    "WorkerTaskPerf",
    "WorkerTaskProfiler",
]
