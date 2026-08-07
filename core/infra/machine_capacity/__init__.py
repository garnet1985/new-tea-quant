"""Machine Capacity（``infra.machine_capacity``）— CPU / 内存容量探测。

公开门面::

    from core.infra.machine_capacity import MachineInfo

容量快照类型::

    from core.infra.machine_capacity.contracts import MachineCapacity
    # 或 MachineInfo.types.MachineCapacity
"""

from .machine_capacity import MachineInfo

__all__ = ["MachineInfo"]
