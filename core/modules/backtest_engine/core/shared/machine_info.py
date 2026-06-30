"""Re-export app-wide machine capacity helpers (implementation in core.infra)."""
from core.infra.machine_capacity import MachineCapacity, MachineInfo

__all__ = ["MachineCapacity", "MachineInfo"]
