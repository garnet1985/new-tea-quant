"""Backtest Engine — shared planner base (machine capacity + plan_jobs API)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from core.infra.machine_capacity.contracts import MachineCapacity


class BasePlanner(ABC):
    """Abstract planner base: ``plan_jobs`` + shared ``_get_machine_capacity``."""

    @classmethod
    @abstractmethod
    def plan_jobs(
        cls,
        jobs: List[Dict[str, Any]],
        performance: Dict[str, Any],
        executor: Optional[Any] = None,
        log_label: str = "调度",
    ) -> Tuple[Any, ...]:
        """Planner orchestration entry; concrete return shape is mode-specific."""
        pass

    @classmethod
    def _get_machine_capacity(
        cls,
        performance: Dict[str, Any],
    ) -> MachineCapacity:
        from core.infra.machine_capacity import MachineInfo

        return MachineInfo.get_capacity(performance)


__all__ = [
    "BasePlanner",
]
