"""枚举层战役落盘（sea）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import PersistBase


class EnumeratePersist(PersistBase):
    LAYER = "enumerate"
    KIND = SimulateKind.ENUMERATE
    TASK_ID = "enumerate"
