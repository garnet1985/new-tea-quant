"""
Bundle 执行进度 — 多线程抓取时供进度监控与限流等待日志共用。
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional

_ACTIVE: Optional["BundleExecutionProgress"] = None
_ACTIVE_LOCK = threading.Lock()

# data_source batch 合并写入 auto 模式的上限
AUTO_MAX_SAVE_BATCH_SIZE = 1000


class BundleExecutionProgress:
    """线程安全的 bundle 抓取进度快照。"""

    def __init__(self, data_source_key: str, total_bundles: int) -> None:
        self.data_source_key = data_source_key
        self.total_bundles = max(int(total_bundles), 0)
        self._lock = threading.Lock()
        self.completed = 0
        self.failed = 0
        self.running = 0
        self.saved_to_db = 0

    def update_from_worker_stats(self, stats: Dict[str, Any]) -> None:
        with self._lock:
            self.completed = int(stats.get("completed_jobs") or 0)
            self.failed = int(stats.get("failed_jobs") or 0)
            self.running = int(stats.get("running_jobs") or 0)

    def add_saved(self, count: int) -> None:
        if count <= 0:
            return
        with self._lock:
            self.saved_to_db += count

    def snapshot(self) -> Dict[str, int]:
        with self._lock:
            done = self.completed + self.failed
            remaining = max(0, self.total_bundles - done)
            pct = int(done / self.total_bundles * 100) if self.total_bundles else 0
            return {
                "completed": self.completed,
                "failed": self.failed,
                "running": self.running,
                "done": done,
                "remaining": remaining,
                "total": self.total_bundles,
                "pct": pct,
                "saved_to_db": self.saved_to_db,
            }

    def format_short(self) -> str:
        s = self.snapshot()
        return (
            f"[{self.data_source_key}] 抓取 {s['done']}/{s['total']} ({s['pct']}%)"
            f"，剩余 {s['remaining']}"
            + (f"，失败 {s['failed']}" if s["failed"] else "")
            + (f"，运行中 {s['running']}" if s["running"] else "")
        )


def install(data_source_key: str, total_bundles: int) -> BundleExecutionProgress:
    global _ACTIVE
    progress = BundleExecutionProgress(data_source_key, total_bundles)
    with _ACTIVE_LOCK:
        _ACTIVE = progress
    return progress


def clear() -> None:
    global _ACTIVE
    with _ACTIVE_LOCK:
        _ACTIVE = None


def current() -> Optional[BundleExecutionProgress]:
    with _ACTIVE_LOCK:
        return _ACTIVE
