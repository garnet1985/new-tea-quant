"""Portfolio 回放汇总（纯数据）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.portfolio.simulator import PortfolioSimResult


@dataclass
class PortfolioSummary:
    """一次 portfolio 回放的全局汇总。"""

    initial_capital: float = 0.0
    final_cash: float = 0.0
    final_equity: float = 0.0
    total_return: float = 0.0
    total_trades: int = 0
    buy_trades: int = 0
    sell_trades: int = 0
    completed_investments: int = 0
    open_positions: int = 0
    win_count: int = 0
    win_rate: float = 0.0
    realized_profit: float = 0.0
    skipped_buys: int = 0
    skipped_sells: int = 0
    buy_participation_skip: int = 0
    buy_participation_clipped: int = 0
    sell_participation_skip: int = 0
    sell_participation_clipped: int = 0
    period: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_sim(
        cls,
        sim: "PortfolioSimResult",
        *,
        period: Dict[str, str],
    ) -> "PortfolioSummary":
        account = sim.account
        initial = float(account.initial_cash)
        final_equity = float(account.equity({}))
        total_return = (final_equity / initial - 1.0) if initial > 0 else 0.0
        sell_profits = [
            float(t.profit or 0.0)
            for t in sim.trades
            if t.is_sell() and t.profit is not None
        ]
        win_rate = (
            (float(sim.win_count) / float(sim.completed_count))
            if sim.completed_count > 0
            else 0.0
        )
        return cls(
            initial_capital=initial,
            final_cash=float(account.cash),
            final_equity=final_equity,
            total_return=total_return,
            total_trades=len(sim.trades),
            buy_trades=sum(1 for t in sim.trades if t.is_buy()),
            sell_trades=sum(1 for t in sim.trades if t.is_sell()),
            completed_investments=int(sim.completed_count),
            open_positions=int(account.open_position_count()),
            win_count=int(sim.win_count),
            win_rate=win_rate,
            realized_profit=float(sum(sell_profits)),
            skipped_buys=int(sim.skipped_buys),
            skipped_sells=int(sim.skipped_sells),
            buy_participation_skip=int(sim.buy_participation_skip),
            buy_participation_clipped=int(sim.buy_participation_clipped),
            sell_participation_skip=int(sim.sell_participation_skip),
            sell_participation_clipped=int(sim.sell_participation_clipped),
            period=dict(period or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initial_capital": self.initial_capital,
            "final_cash": self.final_cash,
            "final_equity": self.final_equity,
            "total_return": self.total_return,
            "total_trades": self.total_trades,
            "buy_trades": self.buy_trades,
            "sell_trades": self.sell_trades,
            "completed_investments": self.completed_investments,
            "open_positions": self.open_positions,
            "win_count": self.win_count,
            "win_rate": self.win_rate,
            "realized_profit": self.realized_profit,
            "skipped_buys": self.skipped_buys,
            "skipped_sells": self.skipped_sells,
            "buy_participation_skip": self.buy_participation_skip,
            "buy_participation_clipped": self.buy_participation_clipped,
            "sell_participation_skip": self.sell_participation_skip,
            "sell_participation_clipped": self.sell_participation_clipped,
            "period": dict(self.period or {}),
        }


__all__ = ["PortfolioSummary"]
