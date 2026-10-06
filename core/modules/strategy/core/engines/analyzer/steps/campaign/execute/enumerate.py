"""枚举层战役执行（sea）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import ExecuteBase


class EnumerateExecute(ExecuteBase):
    LAYER = "enumerate"
    KIND = SimulateKind.ENUMERATE
