"""跨模块契约类型（机器容量快照）。

推荐::

    from core.infra.machine_capacity import MachineInfo
    from core.infra.machine_capacity.contracts import MachineCapacity

亦可::

    MachineInfo.types.MachineCapacity
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MachineCapacity:
    """机器容量信息快照。"""

    cpu_count: int
    memory_budget_mb: float
    memory_floor_mb: float
    reserve_cores: int


__all__ = ["MachineCapacity"]
