"""Workbench step ↔ SimulateKind mapping for analyzer."""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind, WorkbenchStep


class AnalyzerStepMapping:
    @staticmethod
    def value(store_kind: SimulateKind) -> str:
        step = WorkbenchStep.from_simulate_kind(store_kind)
        if step is None:
            raise ValueError(f"unsupported simulation step: {store_kind!r}")
        return step.value

    @staticmethod
    def parse(raw: object) -> WorkbenchStep:
        if isinstance(raw, WorkbenchStep):
            return raw
        if isinstance(raw, SimulateKind):
            step = WorkbenchStep.from_simulate_kind(raw)
            if step is None:
                raise ValueError(f"unsupported simulation step: {raw!r}")
            return step
        return WorkbenchStep.parse(raw)

    @staticmethod
    def to_simulate_kind(step: WorkbenchStep) -> SimulateKind:
        return step.to_simulate_kind()
