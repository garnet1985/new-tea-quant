"""Tag JobPipeline 运行剖面（stage / execute / report）。"""
from __future__ import annotations

import pickle
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class TagRunProfile:
    enabled: bool = False
    stage_sec: float = 0.0
    report_sec: float = 0.0
    execute_sec: float = 0.0
    save_batch_sec: float = 0.0
    stage_jobs: int = 0
    report_jobs: int = 0
    execute_jobs: int = 0
    pickle_bytes: int = 0
    payload_rows: int = 0
    _t0: float = field(default_factory=time.perf_counter)

    def record_stage(self, *, elapsed_sec: float, payload: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        self.stage_sec += elapsed_sec
        self.stage_jobs += 1
        try:
            blob = pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL)
            self.pickle_bytes += len(blob)
        except Exception:
            pass
        inject = payload.get("_inject") or {}
        slot_data = inject.get("slot_data") or {}
        self.payload_rows += sum(len(v or []) for v in slot_data.values())

    def record_execute(self, elapsed_sec: float) -> None:
        if not self.enabled:
            return
        self.execute_sec += elapsed_sec
        self.execute_jobs += 1

    def record_report(self, *, elapsed_sec: float, save_batch_sec: float) -> None:
        if not self.enabled:
            return
        self.report_sec += elapsed_sec
        self.save_batch_sec += save_batch_sec
        self.report_jobs += 1

    def wall_sec(self) -> float:
        return time.perf_counter() - self._t0

    def summary_lines(self, *, total_jobs: int, database_type: str = "") -> List[str]:
        if not self.enabled:
            return []
        wall = self.wall_sec()
        accounted = self.stage_sec + self.execute_sec + self.report_sec
        overhead = max(0.0, wall - accounted)
        avg_pickle = (self.pickle_bytes / self.stage_jobs) if self.stage_jobs else 0
        db_label = f", db={database_type}" if database_type else ""
        lines = [
            "Tag 剖面 (wall=%.2fs, jobs=%s%s):" % (wall, total_jobs, db_label),
            "  stage(worker): %.2fs  (%d jobs, avg %.1fms/job, pickle %.1fKB/job, rows %d)"
            % (
                self.stage_sec,
                self.stage_jobs,
                (self.stage_sec / self.stage_jobs * 1000) if self.stage_jobs else 0,
                avg_pickle / 1024,
                self.payload_rows,
            ),
            "  execute(worker):      %.2fs  (%d jobs, avg %.1fms/job)"
            % (
                self.execute_sec,
                self.execute_jobs,
                (self.execute_sec / self.execute_jobs * 1000) if self.execute_jobs else 0,
            ),
            "  report(on_result):    %.2fs  (save_batch %.2fs, %d jobs, avg %.1fms/job)"
            % (
                self.report_sec,
                self.save_batch_sec,
                self.report_jobs,
                (self.report_sec / self.report_jobs * 1000) if self.report_jobs else 0,
            ),
            "  未计入(调度/pickle IPC/等待): %.2fs (%.0f%%)"
            % (overhead, (overhead / wall * 100) if wall else 0),
        ]
        return lines
