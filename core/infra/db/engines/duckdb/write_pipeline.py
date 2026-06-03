"""
WritePipeline — 单 storage_domain 写 job 队列（域内串行、域间并行）。
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.infra.db.engines.duckdb.engine import DuckdbEngine

logger = logging.getLogger(__name__)


@dataclass
class _WriteJob:
    table_name: str
    op: str  # insert | upsert | delete
    rows: List[Dict[str, Any]] = field(default_factory=list)
    unique_keys: Optional[List[str]] = None
    condition: str = "1=1"
    params: tuple = ()
    limit: Optional[int] = None
    callback: Optional[Callable] = None
    result_holder: List[int] = field(default_factory=list)


class WritePipeline:
    """单个 storage_domain 的写 job 队列 + 单 worker 线程。"""

    def __init__(
        self,
        domain: str,
        engine: "DuckdbEngine",
        *,
        checkpoint_after_write: bool = True,
    ) -> None:
        self.domain = domain
        self._engine = engine
        self.checkpoint_after_write = checkpoint_after_write
        self._queue: List[_WriteJob] = []
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)
        self._stop = False
        self._worker = threading.Thread(
            target=self._run,
            name=f"DuckDB-WritePipeline-{domain}",
            daemon=True,
        )
        self._stats = {"jobs": 0, "rows": 0, "errors": 0}
        self._worker.start()

    def _run(self) -> None:
        while True:
            with self._cv:
                while not self._queue and not self._stop:
                    self._cv.wait(timeout=0.5)
                if self._stop and not self._queue:
                    return
                job = self._queue.pop(0)
            try:
                written = self._execute_job(job)
                if job.result_holder is not None:
                    job.result_holder.append(written)
                if job.callback:
                    job.callback(job.table_name, written)
                with self._lock:
                    self._stats["jobs"] += 1
                    self._stats["rows"] += written
            except Exception as e:
                logger.error(
                    "WritePipeline 执行失败 domain=%s table=%s: %s",
                    self.domain,
                    job.table_name,
                    e,
                )
                with self._lock:
                    self._stats["errors"] += 1
                if job.result_holder is not None:
                    job.result_holder.append(0)
            finally:
                if self.checkpoint_after_write:
                    ok = self._engine.connector.checkpoint(self.domain).get(
                        self.domain, False
                    )
                    if not ok:
                        logger.debug(
                            "批后 CHECKPOINT 延后 domain=%s（写队列仍忙）",
                            self.domain,
                        )

    def _execute_job(self, job: _WriteJob) -> int:
        op = self._engine._table_operator_for_domain(job.table_name, self.domain)
        if job.op == "insert":
            return op._insert_sync(job.rows, job.unique_keys)
        if job.op == "upsert":
            return op._insert_sync(job.rows, job.unique_keys or [])
        if job.op == "delete":
            return op._delete_sync(job.condition, job.params, job.limit)
        return 0

    def submit(self, job: _WriteJob, *, wait: bool = False, timeout: float = 30.0) -> int:
        with self._cv:
            self._queue.append(job)
            self._cv.notify()
        if not wait:
            return 0
        deadline = time.time() + timeout
        while time.time() < deadline:
            if job.result_holder:
                return int(job.result_holder[0])
            time.sleep(0.01)
        logger.warning("WritePipeline wait 超时 domain=%s table=%s", self.domain, job.table_name)
        return 0

    def flush(self, table_name: Optional[str] = None) -> None:
        deadline = time.time() + 30.0
        while time.time() < deadline:
            with self._lock:
                pending = [
                    j
                    for j in self._queue
                    if table_name is None or j.table_name == table_name
                ]
            if not pending:
                return
            time.sleep(0.02)

    def wait(self, timeout: float = 30.0) -> None:
        self.flush()
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                if not self._queue:
                    return
            time.sleep(0.02)

    def shutdown(self) -> None:
        with self._cv:
            self._stop = True
            self._cv.notify_all()
        self._worker.join(timeout=5.0)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._stats)
