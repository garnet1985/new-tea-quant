"""Backtest Engine run progress — phased percent + optional CMD display."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

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


def _phase_percent(phase: RunPhase, *, done: int, total: int) -> float:
    """四个阶段等权。执行阶段的子步骤加在当前阶段上。"""
    from core.infra.progress import Progress

    index = {
        RunPhase.PREP: 0,
        RunPhase.PLAN: 1,
        RunPhase.EXECUTE: 2,
        RunPhase.FINISH: 4,
    }[phase]
    sub = done if phase is RunPhase.EXECUTE else 0
    sub_total = total if phase is RunPhase.EXECUTE else 0
    return Progress.fraction(index, 4, sub, sub_total) * 100.0


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
        if phase is RunPhase.FINISH:
            self._execute_completed = self._execute_total
        self._percent = _phase_percent(
            phase,
            done=self._execute_completed,
            total=self._execute_total,
        )
        if phase is RunPhase.PREP:
            self._phase_floor = self._percent
        elif phase is RunPhase.PLAN:
            self._phase_floor = self._percent
        elif phase is RunPhase.EXECUTE:
            self._phase_floor = _phase_percent(RunPhase.EXECUTE, done=0, total=0)
        snapshot = self.snapshot(phase)
        self._publish(phase)
        self._maybe_display(snapshot, detail=False)
        return snapshot

    def mark_execute_unit(self, completed: int) -> RunProgressSnapshot:
        self._execute_completed = max(0, min(completed, self._execute_total or completed))
        self._percent = _phase_percent(
            RunPhase.EXECUTE,
            done=self._execute_completed,
            total=self._execute_total,
        )
        snapshot = self.snapshot(RunPhase.EXECUTE)
        self._publish(RunPhase.EXECUTE)
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

    def _publish(self, phase: RunPhase) -> None:
        from core.infra.progress import Progress

        current = str(Progress.read().get("job") or "")
        if current and current != "backtest":
            return
        phases = (RunPhase.PREP, RunPhase.PLAN, RunPhase.EXECUTE, RunPhase.FINISH)
        index = phases.index(phase)
        source = self._task_name or "backtest"
        if phase is RunPhase.FINISH:
            Progress.step(len(phases), len(phases), source=source, job="backtest")
            Progress.close()
            return
        Progress.step(index, len(phases), source=source, job="backtest")
        if phase is RunPhase.EXECUTE and self._execute_total > 0:
            Progress.sub(self._execute_completed, self._execute_total, source=source)


__all__ = [
    "RunPhase",
    "RunProgressSnapshot",
    "RunProgressReporter",
    "PHASE_PREP_WEIGHT",
    "PHASE_PLAN_WEIGHT",
    "PHASE_EXECUTE_WEIGHT",
    "PHASE_FINISH_WEIGHT",
]
