"""Run 级依赖袋（create_from_opportunity 注入一次）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence, Tuple, TYPE_CHECKING

from core.modules.strategy.core.engines.shared.services.strategy_settings.simulation_settings.risk_control import (
    RiskControl,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.simulation_settings.tradability import (
    SlippageConfig,
)

from .enums import ExecuteStep

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.shared.services.strategy_settings.goal_settings import (
        GoalSettings,
    )
    from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
        StrategySettings,
    )


@dataclass(frozen=True)
class InvestmentRunDeps:
    """Run-scoped deps — injected once at ``create_from_opportunity`` (``Investment.deps``)."""

    market_rules: Any
    open_dates: Tuple[str, ...]
    goal: "GoalSettings"
    execute_steps: Tuple[ExecuteStep, ...]
    enter_price: str = "next_open"
    exit_price: str = "close"
    monitor_price: str = "close"
    # assumption.tradability.edges — 贴板成交政策（非市场硬规则）
    allow_enter_at_limit_up: bool = False
    allow_exit_at_limit_down: bool = False
    # assumption.tradability.edges.no_next_tick — 样本末无下一 tick 时
    no_next_tick: str = "skip_trade"
    # assumption.tradability.slippage
    slippage: SlippageConfig = field(default_factory=SlippageConfig)
    # assumption.tradability.delisted_exit_price
    delisted_exit_price: str = "last_tradable_close"
    # 提供 ``status_tags_at(entity_id, trade_date)``（如 StockStPeriodsContract）
    status_tags_provider: Any = None
    # simulation.risk_control（skip_enter / force_exit）
    risk: RiskControl = field(default_factory=lambda: RiskControl(raw_settings={}))

    @classmethod
    def from_settings(
        cls,
        *,
        settings: "StrategySettings",
        market_rules: Any,
        open_dates: Sequence[str],
        status_tags_provider: Any = None,
    ) -> "InvestmentRunDeps":
        sim = settings.simulation
        sim.apply_defaults()
        tradability = sim.tradability
        return cls(
            market_rules=market_rules,
            open_dates=tuple(open_dates),
            goal=settings.goal,
            execute_steps=tuple(sim.parsed_execute_steps()),
            enter_price=str(sim.enter_price or "next_open"),
            exit_price=str(sim.exit_price or "close"),
            monitor_price=str(sim.monitor_price or "close"),
            allow_enter_at_limit_up=bool(sim.allow_enter_at_limit_up),
            allow_exit_at_limit_down=bool(sim.allow_exit_at_limit_down),
            no_next_tick=str(
                tradability.edges.no_next_tick or "skip_trade"
            ).strip().lower()
            or "skip_trade",
            slippage=tradability.slippage,
            delisted_exit_price=str(
                sim.delisted_exit_price or "last_tradable_close"
            ).strip().lower()
            or "last_tradable_close",
            status_tags_provider=status_tags_provider,
            risk=sim.risk_control,
        )


__all__ = ["InvestmentRunDeps"]
