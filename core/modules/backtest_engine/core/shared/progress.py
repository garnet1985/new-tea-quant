"""Backtest Engine run progress — phased percent + optional CMD display."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)

PHASE_PREP_WEIGHT = 0.05
PHASE_PLAN_WEIGHT = 0.10
PHASE_EXECUTE_WEIGHT = 0.80
PHASE_FINISH_WEIGHT = 0.05


class RunPhase(str, Enum):
    PREP = "prep"
    PLAN = "plan"
    EXECUTE = "execute"
    FINISH = "finish"


@dataclass(frozen=True)
class RunProgressSnapshot:
    phase: RunPhase
    percent: float
    execute_completed: int = 0
    execute_total: int = 0


class RunProgressReporter:
    """Compute phased run progress; optionally display to CMD (BE-internal)."""

    def __init__(
        self,
        *,
        task_name: str,
        run_mode: str,
        execute_total: int = 0,
        enable_progress_display: bool = True,
    ) -> None:
        self._task_name = task_name or "backtest"
        self._run_mode = run_mode
        self._execute_total = max(0, execute_total)
        self._enable_display = enable_progress_display
        self._phase_floor = 0.0
        self._execute_completed = 0
        self._percent = 0.0

    @property
    def percent(self) -> float:
        return self._percent

    @property
    def execute_total(self) -> int:
        return self._execute_total

    def set_execute_total(self, total: int) -> None:
        self._execute_total = max(0, total)

    def mark_phase(self, phase: RunPhase) -> RunProgressSnapshot:
        if phase is RunPhase.PREP:
            self._phase_floor = PHASE_PREP_WEIGHT * 100.0
            self._percent = self._phase_floor
        elif phase is RunPhase.PLAN:
            self._phase_floor = (PHASE_PREP_WEIGHT + PHASE_PLAN_WEIGHT) * 100.0
            self._percent = self._phase_floor
        elif phase is RunPhase.EXECUTE:
            self._phase_floor = (PHASE_PREP_WEIGHT + PHASE_PLAN_WEIGHT) * 100.0
            self._percent = self._phase_floor
        elif phase is RunPhase.FINISH:
            self._percent = 100.0
        snapshot = self.snapshot(phase)
        self._maybe_display(snapshot, detail=False)
        return snapshot

    def mark_execute_unit(self, completed: int) -> RunProgressSnapshot:
        self._execute_completed = max(0, min(completed, self._execute_total or completed))
        if self._execute_total > 0:
            execute_ratio = self._execute_completed / self._execute_total
        else:
            execute_ratio = 1.0 if self._execute_completed > 0 else 0.0
        self._percent = self._phase_floor + execute_ratio * PHASE_EXECUTE_WEIGHT * 100.0
        snapshot = self.snapshot(RunPhase.EXECUTE)
        self._maybe_display(snapshot, detail=True)
        return snapshot

    def snapshot(self, phase: RunPhase) -> RunProgressSnapshot:
        return RunProgressSnapshot(
            phase=phase,
            percent=min(100.0, max(0.0, self._percent)),
            execute_completed=self._execute_completed,
            execute_total=self._execute_total,
        )

    def make_execute_unit_hook(self) -> Callable[[int], None]:
        def _hook(completed: int) -> None:
            self.mark_execute_unit(completed)

        return _hook

    @staticmethod
    def report_from_payload(payload: dict, completed: int) -> None:
        """Orchestrator: invoke engine-injected ``_engine_on_execute_unit_done`` (CMD)."""
        hook = payload.get("_engine_on_execute_unit_done")
        if callable(hook):
            hook(completed)

    def _maybe_display(self, snapshot: RunProgressSnapshot, *, detail: bool) -> None:
        if not self._enable_display:
            return
        total_line = (
            f"任务：{self._task_name} {self._run_mode} "
            f"执行总进度：{snapshot.percent:.0f}%"
        )
        if detail and snapshot.execute_total > 0:
            line = (
                f"任务：{self._task_name} {self._run_mode} "
                f"回测进度：{snapshot.execute_completed}/{snapshot.execute_total}，"
                f"执行总进度：{snapshot.percent:.0f}%"
            )
        else:
            line = total_line
        print(line, flush=True)
        logger.info(line)


__all__ = [
    "RunPhase",
    "RunProgressSnapshot",
    "RunProgressReporter",
    "PHASE_PREP_WEIGHT",
    "PHASE_PLAN_WEIGHT",
    "PHASE_EXECUTE_WEIGHT",
    "PHASE_FINISH_WEIGHT",
]
