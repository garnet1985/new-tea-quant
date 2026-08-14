"""Strategy 模块全局枚举（跨引擎 / Facade / BFF 共用）。

本文件:
- ExecutionMode: scan vs simulate
- SellReason: 卖出原因标签
- SimulateKind: Facade ``Strategy.simulate`` 子步骤（enumerate / price_factor / portfolio / full）
- WorkbenchStep: 工作台 / BFF HTTP 三步（enum / price / portfolio）
  边界: 仅枚举与互转；不含 Pipeline 映射或业务逻辑
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class ExecutionMode(Enum):
    """执行模式。"""

    SCAN = "scan"
    SIMULATE = "simulate"


class SellReason(Enum):
    """卖出原因。"""

    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    MAX_HOLDING = "max_holding"
    END_OF_PERIOD = "end_of_period"


class SimulateKind(Enum):
    """模拟类型（Facade simulate 的 step）。"""

    ENUMERATE = "enumerate"
    PRICE_FACTOR = "price_factor"
    PORTFOLIO = "portfolio"
    FULL = "full"


class WorkbenchStep(Enum):
    """工作台三步（BFF 路径 ``step`` / UI Tab；与 ``SimulateKind`` 一一对应）。

    - ``ENUM`` → enumerate / result_report 槽 ``enum``
    - ``PRICE`` → price_factor / 槽 ``price_factor``
    - ``PORTFOLIO`` → portfolio / 槽 ``portfolio``
    """

    ENUM = "enum"
    PRICE = "price"
    PORTFOLIO = "portfolio"

    @classmethod
    def try_parse(cls, raw: object) -> Optional["WorkbenchStep"]:
        text = str(raw or "").strip().lower()
        if not text:
            return None
        # 核心 kind / 槽名偶发传入时一并认（不含已废弃的 capital）
        aliases = {
            "enumerate": cls.ENUM,
            "price_factor": cls.PRICE,
        }
        if text in aliases:
            return aliases[text]
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
        return {
            WorkbenchStep.ENUM: SimulateKind.ENUMERATE,
            WorkbenchStep.PRICE: SimulateKind.PRICE_FACTOR,
            WorkbenchStep.PORTFOLIO: SimulateKind.PORTFOLIO,
        }[self]

    @classmethod
    def from_simulate_kind(cls, kind: SimulateKind) -> Optional["WorkbenchStep"]:
        mapping = {
            SimulateKind.ENUMERATE: cls.ENUM,
            SimulateKind.PRICE_FACTOR: cls.PRICE,
            SimulateKind.PORTFOLIO: cls.PORTFOLIO,
        }
        return mapping.get(kind)

    @property
    def report_slot(self) -> str:
        """``result_report`` 槽位 key。"""
        return {
            WorkbenchStep.ENUM: "enum",
            WorkbenchStep.PRICE: "price_factor",
            WorkbenchStep.PORTFOLIO: "portfolio",
        }[self]


__all__ = ["ExecutionMode", "SellReason", "SimulateKind", "WorkbenchStep"]
