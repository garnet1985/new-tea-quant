"""Backtest Engine run progress — phased percent + optional CMD display."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Iterator, Optional

class RunPhase(str, Enum):
    PREP = "prep"
    PLAN = "plan"
    EXECUTE = "execute"
    FINISH = "finish"


# 执行占 94。准备、计划、收尾各占 2。
_PHASE_WEIGHTS = {
    RunPhase.PREP: 2,
    RunPhase.PLAN: 2,
    RunPhase.EXECUTE: 94,
    RunPhase.FINISH: 2,
}


def phase_steps(parent_id: str) -> list:
    """一轮回测里的四个阶段。权重沿用单次回测。"""
    return [
        {
            "id": f"{parent_id}:{phase.value}",
            "label": _PHASE_LABELS[phase],
            "weight": _PHASE_WEIGHTS[phase],
        }
        for phase in (RunPhase.PREP, RunPhase.PLAN, RunPhase.EXECUTE, RunPhase.FINISH)
    ]


_PHASE_LABELS = {
    RunPhase.PREP: "准备",
    RunPhase.PLAN: "计划",
    RunPhase.EXECUTE: "执行",
    RunPhase.FINISH: "收尾",
}


@dataclass(frozen=True)
class ProgressRound:
    """多轮任务里，这一轮在总进度中的位置。"""

    root_id: str
    round_id: str
    index: int
    total: int


_ATTACHED: ContextVar[Optional[ProgressRound]] = ContextVar(
    "backtest_progress_round", default=None
)


@contextmanager
def attach_round(root_id: str, round_id: str, *, index: int, total: int) -> Iterator[str]:
    """这一轮回测写入已有的总进度，不再单独从 0 走到 100。"""
    token = _ATTACHED.set(
        ProgressRound(
            root_id=str(root_id),
            round_id=str(round_id),
            index=int(index),
            total=int(total),
        )
    )
    try:
        yield str(round_id)
    finally:
        _ATTACHED.reset(token)


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
        self._attached = _ATTACHED.get()

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
        head = f"任务：{self._task_name} {self._run_mode} "
        attached = self._attached
        if attached is not None and attached.total > 1:
            head += f"第 {attached.index}/{attached.total} 轮，"
        if detail and snapshot.execute_total > 0:
            line = (
                f"{head}"
                f"回测进度：{snapshot.execute_completed}/{snapshot.execute_total}，"
                f"执行总进度：{snapshot.percent:.0f}%"
            )
        else:
            line = f"{head}执行总进度：{snapshot.percent:.0f}%"
        print(line, flush=True)

    def _progress_root(self) -> str:
        raw = self._task_name or "backtest"
        safe = raw.replace("/", "-").replace("\\", "-").strip() or "backtest"
        return f"backtest-{safe}"

    def _scope_id(self) -> str:
        if self._attached is not None:
            return self._attached.round_id
        return self._progress_root()

    def _ensure_progress(self) -> str:
        scope = self._scope_id()
        if getattr(self, "_progress_ready", False):
            return scope
        if self._attached is None:
            Progress = _progress_type()
            Progress.start(
                scope,
                job="backtest",
                label=self._task_name or "backtest",
                steps=phase_steps(scope),
            )
        self._progress_ready = True
        return scope

    def _sync_percent(self, node_id: str) -> None:
        document = _progress_type().read(node_id)
        if not document:
            return
        self._percent = float(document.get("ratio") or 0) * 100.0

    def _publish(self, phase: RunPhase) -> None:
        scope = self._ensure_progress()
        progress = _progress_type()
        if self._attached is not None:
            progress.resume(scope)
        if phase is RunPhase.FINISH and self._attached is None:
            progress.finish(scope)
            self._sync_percent(scope)
            return
        order = (RunPhase.PREP, RunPhase.PLAN, RunPhase.EXECUTE, RunPhase.FINISH)
        index = order.index(phase)
        for earlier in order[:index]:
            progress.finish(f"{scope}:{earlier.value}")
        if phase is RunPhase.FINISH:
            progress.finish(f"{scope}:{phase.value}")
            self._sync_percent(scope)
            return
        if phase is RunPhase.EXECUTE and self._execute_total > 0:
            done, total = self._execute_completed, self._execute_total
        else:
            done, total = 0, 1
        progress.tick(
            f"{scope}:{phase.value}",
            done,
            total,
            source=self._task_name or "backtest",
            log=False,
        )
        self._sync_percent(scope)


def _progress_type():
    from core.infra.progress import Progress

    return Progress


__all__ = [
    "RunPhase",
    "RunProgressSnapshot",
    "RunProgressReporter",
    "attach_round",
    "phase_steps",
]
