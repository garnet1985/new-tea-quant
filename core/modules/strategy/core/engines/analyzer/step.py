"""Analyzer 对外 step 与 ArtifactStore SimulateKind 互转。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind, WorkbenchStep


def step_value(store_kind: SimulateKind) -> str:
    """SimulateKind → 工作台 step（enum / price / portfolio）。"""
    step = WorkbenchStep.from_simulate_kind(store_kind)
    if step is None:
        raise ValueError(f"unsupported simulation step: {store_kind!r}")
    return step.value


def parse_step(raw: object) -> WorkbenchStep:
    """CLI / Facade 入参 → WorkbenchStep。"""
    if isinstance(raw, WorkbenchStep):
        return raw
    if isinstance(raw, SimulateKind):
        step = WorkbenchStep.from_simulate_kind(raw)
        if step is None:
            raise ValueError(f"unsupported simulation step: {raw!r}")
        return step
    return WorkbenchStep.parse(raw)


def step_to_simulate_kind(step: WorkbenchStep) -> SimulateKind:
    return step.to_simulate_kind()


__all__ = ["parse_step", "step_to_simulate_kind", "step_value"]
