"""Strategy 模块全局枚举（跨引擎 / Facade / BFF 共用）。

本文件:
- SimulateKind: Facade ``Strategy.simulate`` 子步骤（enum / price / portfolio / full）
- WorkbenchStep: 工作台 / BFF HTTP 三步（enum / price / portfolio）
  边界: 仅枚举与互转；不含 Pipeline 映射或业务逻辑
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class SimulateKind(Enum):
    """模拟类型（Facade simulate 的 step）。"""

    ENUMERATE = "enum"
    PRICE_FACTOR = "price"
    PORTFOLIO = "portfolio"
    # TODO: 一次跑完三步的 full 还没接入，入口先拒绝。以后可能要。
    FULL = "full"


class WorkbenchStep(Enum):
    """工作台三步（BFF 路径 ``step`` / UI Tab）。值与 ``SimulateKind`` 相同。"""

    ENUM = "enum"
    PRICE = "price"
    PORTFOLIO = "portfolio"

    @classmethod
    def try_parse(cls, raw: object) -> Optional["WorkbenchStep"]:
        text = str(raw or "").strip().lower()
        if not text:
            return None
        try:
            return cls(text)
        except ValueError:
            return None

    @classmethod
    def parse(cls, raw: object) -> "WorkbenchStep":
        step = cls.try_parse(raw)
        if step is None:
            raise ValueError("step 须为 enum / price / portfolio")
        return step

    @classmethod
    def values(cls) -> frozenset:
        return frozenset(m.value for m in cls)

    def to_simulate_kind(self) -> SimulateKind:
        return SimulateKind(self.value)

    @property
    def report_slot(self) -> str:
        """``result_report`` 槽位 key，与步骤名相同。"""
        return self.value


__all__ = ["SimulateKind", "WorkbenchStep"]
