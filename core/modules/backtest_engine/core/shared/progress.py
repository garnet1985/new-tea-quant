"""Backtest Engine run progress — phased percent + optional CMD display."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

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
        if phase is RunPhase.FINISH:
            self._execute_completed = self._execute_total
        self._publish(phase)
        self._phase_floor = self._percent
        snapshot = self.snapshot(phase)
        self._maybe_display(snapshot, detail=False)
        return snapshot

    def mark_execute_unit(self, completed: int) -> RunProgressSnapshot:
        self._execute_completed = max(0, min(completed, self._execute_total or completed))
        self._publish(RunPhase.EXECUTE)
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

    def _progress_root(self) -> str:
        raw = self._task_name or "backtest"
        safe = raw.replace("/", "-").replace("\\", "-").strip() or "backtest"
        return f"backtest-{safe}"

    def _ensure_progress(self) -> str:
        root = self._progress_root()
        if getattr(self, "_progress_ready", False):
            return root
        Progress = _progress_type()
        Progress.start(
            root,
            job="backtest",
            label=self._task_name or "backtest",
            steps=[
                {"id": f"{root}:prep", "label": "准备"},
                {"id": f"{root}:plan", "label": "计划"},
                {"id": f"{root}:execute", "label": "执行"},
                {"id": f"{root}:finish", "label": "收尾"},
            ],
        )
        self._progress_ready = True
        return root

    def _sync_percent(self, root: str) -> None:
        document = _progress_type().read(root)
        if not document:
            return
        self._percent = float(document.get("ratio") or 0) * 100.0

    def _publish(self, phase: RunPhase) -> None:
        root = self._ensure_progress()
        progress = _progress_type()
        if phase is RunPhase.FINISH:
            progress.finish(root)
            self._sync_percent(root)
            return
        order = (RunPhase.PREP, RunPhase.PLAN, RunPhase.EXECUTE)
        index = order.index(phase)
        for earlier in order[:index]:
            progress.finish(f"{root}:{earlier.value}")
        if phase is RunPhase.EXECUTE and self._execute_total > 0:
            done, total = self._execute_completed, self._execute_total
        else:
            done, total = 0, 1
        progress.tick(
            f"{root}:{phase.value}",
            done,
            total,
            source=self._task_name or "backtest",
            log=False,
        )
        self._sync_percent(root)


def _progress_type():
    from core.infra.progress import Progress

    return Progress


__all__ = [
    "RunPhase",
    "RunProgressSnapshot",
    "RunProgressReporter",
]
