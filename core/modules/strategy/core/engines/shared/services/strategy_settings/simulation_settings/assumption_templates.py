"""``simulation.assumption.template`` — 命名成交假设预设（仅 tradability）。"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, ClassVar, Dict, FrozenSet

from .tradability import TradabilityConfig


class AssumptionTemplate:
    """命名预设：短路填充 ``assumption.tradability``。

    ``none`` / ``custom`` / 缺省 → 使用显式 tradability，不走本类快照。
    风险对策不在此（见 ``RiskControl``）。
    """

    STANDARD: ClassVar[str] = "standard"
    STRICT: ClassVar[str] = "strict"
    IDEAL: ClassVar[str] = "ideal"
    EXTREME: ClassVar[str] = "extreme"
    NONE: ClassVar[str] = "none"
    CUSTOM: ClassVar[str] = "custom"

    NAMED: ClassVar[FrozenSet[str]] = frozenset(
        {STANDARD, STRICT, IDEAL, EXTREME}
    )
    EXPLICIT: ClassVar[FrozenSet[str]] = frozenset({NONE, CUSTOM})
    KNOWN: ClassVar[FrozenSet[str]] = NAMED | EXPLICIT

    @classmethod
    def canonicalize(cls, raw: Any) -> str:
        text = str(raw or "").strip().lower()
        if not text or text == cls.NONE:
            return cls.NONE
        if text == cls.CUSTOM:
            return cls.CUSTOM
        if text in cls.NAMED:
            return text
        raise ValueError(
            f"assumption.template 非法: {raw!r}；允许 {sorted(cls.KNOWN)}"
        )

    @classmethod
    def is_named(cls, raw: Any) -> bool:
        try:
            return cls.canonicalize(raw) in cls.NAMED
        except ValueError:
            return False

    @classmethod
    def tradability(cls, template: str) -> TradabilityConfig:
        """命名预设 → ``TradabilityConfig``。"""
        key = cls.canonicalize(template)
        if key == cls.STANDARD:
            return TradabilityConfig.from_raw(
                {
                    "monitor_price": "close",
                    "enter_price": "next_open",
                    "exit_price": "close",
                    "edges": {
                        "allow_enter_at_limit_up": False,
                        "allow_exit_at_limit_down": False,
                    },
                    "liquidity": {
                        "max_participation_rate": 0.1,
                        "participation_on_exceed": "clip",
                    },
                }
            )
        if key == cls.STRICT:
            return TradabilityConfig.from_raw(
                {
                    "monitor_price": "close",
                    "enter_price": "next_open",
                    "exit_price": "close",
                    "edges": {
                        "allow_enter_at_limit_up": False,
                        "allow_exit_at_limit_down": False,
                    },
                    "liquidity": {
                        "max_participation_rate": 0.1,
                        "participation_on_exceed": "skip",
                    },
                }
            )
        if key == cls.IDEAL:
            return TradabilityConfig.from_raw(
                {
                    "monitor_price": "close",
                    "enter_price": "next_open",
                    "exit_price": "close",
                    "edges": {
                        "allow_enter_at_limit_up": True,
                        "allow_exit_at_limit_down": True,
                    },
                    "liquidity": {
                        "max_participation_rate": 0.1,
                        "participation_on_exceed": "clip",
                    },
                }
            )
        if key == cls.EXTREME:
            return TradabilityConfig.from_raw(
                {
                    "monitor_price": "extreme",
                    "enter_price": "extreme",
                    "exit_price": "extreme",
                    "edges": {
                        "allow_enter_at_limit_up": True,
                        "allow_exit_at_limit_down": True,
                    },
                    "liquidity": {
                        "max_participation_rate": 0.1,
                        "participation_on_exceed": "skip",
                    },
                }
            )
        raise ValueError(
            f"assumption.template {template!r} 不是命名预设；"
            f"命名预设: {sorted(cls.NAMED)}"
        )

    @classmethod
    def tradability_dict(cls, template: str) -> Dict[str, Any]:
        return deepcopy(cls.tradability(template).to_dict())


__all__ = ["AssumptionTemplate"]
