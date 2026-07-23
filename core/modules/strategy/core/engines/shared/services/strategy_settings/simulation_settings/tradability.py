"""``simulation.assumption.tradability`` — 成交假设（盯价 / 进出价 / 贴板 / 参与率）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, Optional, Tuple


_KNOWN_DELISTED_EXIT_PRICES = frozenset({"last_tradable_close", "same_tick_close"})
_KNOWN_NO_NEXT_TICK = frozenset({"skip_trade", "use_last_close"})


@dataclass(frozen=True)
class EdgesConfig:
    """贴板是否允许成交（仿真假设，非市场硬规则）。"""

    allow_enter_at_limit_up: bool = False
    allow_exit_at_limit_down: bool = False
    no_next_tick: str = "skip_trade"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "no_next_tick": self.no_next_tick,
            "allow_enter_at_limit_up": self.allow_enter_at_limit_up,
            "allow_exit_at_limit_down": self.allow_exit_at_limit_down,
        }


@dataclass(frozen=True)
class SlippageConfig:
    enter_bps: float = 0.0
    exit_bps: float = 0.0

    def apply_enter(self, price: float) -> float:
        """进场：对理论价上浮 ``enter_bps``。"""
        px = float(price)
        if px <= 0:
            return px
        return px * (1.0 + max(0.0, float(self.enter_bps)) / 10_000.0)

    def apply_exit(self, price: float) -> float:
        """出场：对理论价下浮 ``exit_bps``。"""
        px = float(price)
        if px <= 0:
            return px
        return px * (1.0 - max(0.0, float(self.exit_bps)) / 10_000.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enter_bps": float(self.enter_bps),
            "exit_bps": float(self.exit_bps),
        }


@dataclass(frozen=True)
class LiquidityConfig:
    """tick 成交量参与率。上限股数 ≈ ``tick.volume × max_participation_rate``。"""

    ON_EXCEED_CLIP: ClassVar[str] = "clip"
    ON_EXCEED_SKIP: ClassVar[str] = "skip"
    ALLOWED_ON_EXCEED: ClassVar[frozenset] = frozenset({"clip", "skip"})

    TAG_SKIP: ClassVar[str] = "participation_skip"
    TAG_CLIP_ZERO: ClassVar[str] = "participation_clip_zero"
    TAG_CLIPPED: ClassVar[str] = "participation_clipped"

    max_participation_rate: float = 0.1
    participation_on_exceed: str = "clip"

    @classmethod
    def from_raw(
        cls,
        raw: Any,
        *,
        field_path: str = "simulation.assumption.tradability.liquidity",
    ) -> "LiquidityConfig":
        if raw is None:
            return cls()
        if not isinstance(raw, dict):
            raise ValueError(f"{field_path} 必须为 dict")
        rate = cls._parse_rate(
            raw.get("max_participation_rate"), default=0.1, field_path=field_path
        )
        on_exceed = cls._parse_on_exceed(
            raw.get("participation_on_exceed"), field_path=field_path
        )
        return cls(max_participation_rate=rate, participation_on_exceed=on_exceed)

    @classmethod
    def _parse_rate(cls, raw: Any, *, default: float, field_path: str) -> float:
        if raw is None or raw == "":
            return float(default)
        try:
            rate = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{field_path}.max_participation_rate 须为 (0, 1] 内数字"
            ) from exc
        if rate <= 0.0 or rate > 1.0:
            raise ValueError(
                f"{field_path}.max_participation_rate 须在 (0, 1] 内；1 表示不限制"
            )
        return rate

    @classmethod
    def _parse_on_exceed(cls, raw: Any, *, field_path: str) -> str:
        if raw is None or raw == "":
            return cls.ON_EXCEED_CLIP
        key = str(raw).strip().lower()
        if key not in cls.ALLOWED_ON_EXCEED:
            raise ValueError(
                f"{field_path}.participation_on_exceed 非法: {raw!r}；"
                f"允许 {sorted(cls.ALLOWED_ON_EXCEED)}"
            )
        return key

    def max_shares(self, tick_volume: Optional[float]) -> Optional[int]:
        """``None`` = 不限制；``0`` = 无可成交额度。"""
        if self.max_participation_rate >= 1.0 - 1e-12:
            return None
        if tick_volume is None:
            return None
        if float(tick_volume) <= 0:
            return 0
        return int(float(tick_volume) * float(self.max_participation_rate))

    def apply_to_shares(
        self,
        planned_shares: int,
        *,
        tick_volume: Optional[float],
        floor_shares_fn,
        entity_id: str,
    ) -> Tuple[int, Optional[str]]:
        """返回 ``(最终股数, 结果标记)``。"""
        planned = max(int(planned_shares or 0), 0)
        if planned <= 0:
            return 0, None

        cap = self.max_shares(tick_volume)
        if cap is None:
            floored = int(floor_shares_fn(planned, entity_id))
            if floored <= 0:
                return 0, self.TAG_SKIP
            return floored, None
        if cap <= 0:
            return 0, self.TAG_SKIP

        if planned <= cap:
            floored = int(floor_shares_fn(planned, entity_id))
            if floored <= 0:
                return 0, self.TAG_SKIP
            return floored, None

        if self.participation_on_exceed == self.ON_EXCEED_SKIP:
            return 0, self.TAG_SKIP

        clipped = int(floor_shares_fn(cap, entity_id))
        if clipped <= 0:
            return 0, self.TAG_CLIP_ZERO
        if clipped < planned:
            return clipped, self.TAG_CLIPPED
        return clipped, None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_participation_rate": float(self.max_participation_rate),
            "participation_on_exceed": str(self.participation_on_exceed),
        }


@dataclass(frozen=True)
class TradabilityConfig:
    """解析后的 ``assumption.tradability`` 快照。"""

    monitor_price: str = "close"
    enter_price: str = "next_open"
    exit_price: str = "close"
    slippage: SlippageConfig = field(default_factory=SlippageConfig)
    edges: EdgesConfig = field(default_factory=EdgesConfig)
    liquidity: LiquidityConfig = field(default_factory=LiquidityConfig)
    delisted_exit_price: str = "last_tradable_close"

    @classmethod
    def from_raw(
        cls,
        raw: Any,
        *,
        field_path: str = "simulation.assumption.tradability",
    ) -> "TradabilityConfig":
        if raw is None:
            raw = {}
        if not isinstance(raw, dict):
            raise ValueError(f"{field_path} 必须为 dict")

        if "edges" in raw and raw.get("edges") is not None and not isinstance(
            raw.get("edges"), dict
        ):
            raise ValueError(f"{field_path}.edges 必须为 dict")

        edges_raw = raw.get("edges") if isinstance(raw.get("edges"), dict) else {}
        no_next = str(edges_raw.get("no_next_tick") or "skip_trade").strip().lower()
        if no_next not in _KNOWN_NO_NEXT_TICK:
            raise ValueError(
                f"{field_path}.edges.no_next_tick 非法: {no_next!r}；"
                f"允许 {sorted(_KNOWN_NO_NEXT_TICK)}"
            )

        slip_raw = raw.get("slippage") if isinstance(raw.get("slippage"), dict) else {}
        delisted = str(
            raw.get("delisted_exit_price") or "last_tradable_close"
        ).strip().lower()
        if delisted not in _KNOWN_DELISTED_EXIT_PRICES:
            raise ValueError(
                f"{field_path}.delisted_exit_price 非法: {delisted!r}；"
                f"允许 {sorted(_KNOWN_DELISTED_EXIT_PRICES)}"
            )

        return cls(
            monitor_price=str(raw.get("monitor_price") or "close").strip().lower()
            or "close",
            enter_price=str(raw.get("enter_price") or "next_open").strip().lower()
            or "next_open",
            exit_price=str(raw.get("exit_price") or "close").strip().lower() or "close",
            slippage=SlippageConfig(
                enter_bps=float(slip_raw.get("enter_bps") or 0.0),
                exit_bps=float(slip_raw.get("exit_bps") or 0.0),
            ),
            edges=EdgesConfig(
                allow_enter_at_limit_up=bool(
                    edges_raw.get("allow_enter_at_limit_up", False)
                ),
                allow_exit_at_limit_down=bool(
                    edges_raw.get("allow_exit_at_limit_down", False)
                ),
                no_next_tick=no_next,
            ),
            liquidity=LiquidityConfig.from_raw(
                raw.get("liquidity"),
                field_path=f"{field_path}.liquidity",
            ),
            delisted_exit_price=delisted,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "monitor_price": self.monitor_price,
            "enter_price": self.enter_price,
            "exit_price": self.exit_price,
            "slippage": self.slippage.to_dict(),
            "edges": self.edges.to_dict(),
            "liquidity": self.liquidity.to_dict(),
            "delisted_exit_price": self.delisted_exit_price,
        }

    @classmethod
    def default(cls) -> "TradabilityConfig":
        return cls.from_raw({})


__all__ = [
    "EdgesConfig",
    "LiquidityConfig",
    "SlippageConfig",
    "TradabilityConfig",
]
