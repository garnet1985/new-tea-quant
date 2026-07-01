"""Flow 内阶段进度句柄：可选注入工作台 run。"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

StepStageFn = Callable[[str, str, float, Optional[Dict[str, Any]]], None]


class WorkbenchFlowProgress:
    """``stage()`` 写 load/dispatch/report；``__call__(pct)`` 写 execute（0～100）。"""

    __slots__ = ("_fn", "_substep")

    def __init__(self, on_stage: StepStageFn, substep: str) -> None:
        self._fn = on_stage
        self._substep = str(substep).strip()

    def stage(
        self,
        stage: str,
        ratio: float = 0.0,
        *,
        counters: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._fn(self._substep, str(stage).strip(), float(ratio), counters)

    def __call__(self, pct: float) -> None:
        self.stage("execute", float(pct) / 100.0)


__all__ = ["StepStageFn", "WorkbenchFlowProgress"]
