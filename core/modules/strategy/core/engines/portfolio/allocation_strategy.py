"""Portfolio 仓位 sizing（equal_capital / equal_shares / kelly）。

本文件:
- AllocationStrategy: 给定 buy 事件与账户快照计算股数
  边界: 负责「买多少」；不负责选仓或费率以外的账户逻辑

同进程持有 ``StrategySettings`` 引用，不把 portfolio/liquidity 再投影成标量袋。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

from core.modules.market_profile.contracts import MarketBaseRules
from core.modules.strategy.core.engines.portfolio.data_class.account import Account
from core.modules.strategy.core.engines.portfolio.fee_calculator import FeeCalculator
from core.modules.strategy.core.engines.shared.services.strategy_settings.portfolio_settings import (
    AllocationConfig,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.simulation_settings import (
    LiquidityConfig,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)


@dataclass
class AllocationStrategy:
    """按配置计算买入股数（只算多少，不选谁）。"""

    settings: StrategySettings
    market_rules: MarketBaseRules
    fee_calculator: FeeCalculator
    _mode: str = "equal_capital"

    @classmethod
    def create(
        cls,
        *,
        settings: StrategySettings,
        market_rules: MarketBaseRules,
        fee_calculator: Optional[FeeCalculator] = None,
    ) -> "AllocationStrategy":
        alloc: AllocationConfig = settings.portfolio.allocation
        mode = str(alloc.mode or "equal_capital").strip().lower()
        if mode == "custom":
            mode = "equal_capital"
        if mode not in {"equal_capital", "equal_shares", "kelly"}:
            raise ValueError(f"unsupported allocation.mode: {alloc.mode!r}")
        return cls(
            settings=settings,
            market_rules=market_rules,
            fee_calculator=fee_calculator or FeeCalculator(),
            _mode=mode,
        )

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def initial_capital(self) -> float:
        return float(self.settings.portfolio.initial_capital)

    @property
    def max_portfolio_size(self) -> int:
        return int(self.settings.portfolio.allocation.max_portfolio_size)

    @property
    def lots_per_trade(self) -> int:
        return max(int(self.settings.portfolio.allocation.lots_per_trade or 1), 1)

    @property
    def kelly_fraction(self) -> float:
        return float(self.settings.portfolio.allocation.kelly_fraction)

    @property
    def default_cash(self) -> float:
        return float(self.settings.portfolio.allocation.default_cash or 0.0)

    @property
    def default_shares(self) -> int:
        return int(self.settings.portfolio.allocation.default_shares or 0)

    @property
    def skip_trade_when_insufficient(self) -> bool:
        return bool(self.settings.portfolio.allocation.skip_trade_when_insufficient)

    @property
    def liquidity(self) -> LiquidityConfig:
        return self.settings.simulation.liquidity

    @property
    def per_trade_capital(self) -> float:
        size = max(int(self.max_portfolio_size), 1)
        return float(self.initial_capital) / float(size)

    def calculate_shares_to_buy(
        self,
        account: Account,
        buy_price: float,
        entity_id: str,
        *,
        win_rate: Optional[float] = None,
        payoff: Optional[float] = None,
    ) -> int:
        px = float(buy_price or 0.0)
        if px <= 0 or account.cash <= 0:
            return 0
        if self.mode == "equal_capital":
            return self._equal_capital(account, px, entity_id)
        if self.mode == "equal_shares":
            return self._equal_shares(account, px, entity_id)
        if self.mode == "kelly":
            return self._kelly(account, px, entity_id, win_rate, payoff)
        return 0

    def floor_shares(self, shares: int, entity_id: str) -> int:
        return int(
            self.market_rules.floor_quantity_for_stock(max(int(shares), 0), entity_id)
        )

    def shares_from_cash(self, cash: float, buy_price: float, entity_id: str) -> int:
        """预算金额按成交价换成股数，再向下取整到合法申报数量。"""
        px = float(buy_price or 0.0)
        budget = float(cash or 0.0)
        if px <= 0 or budget <= 0:
            return 0
        planned = self.floor_shares(int(budget / px), entity_id)
        return self._resolve_planned(
            planned_shares=planned,
            entity_id=entity_id,
            cash=budget,
            buy_price=px,
        )

    def apply_participation(
        self,
        planned_shares: int,
        *,
        bar_volume: Optional[float],
        entity_id: str,
    ) -> Tuple[int, Optional[str]]:
        """按 ``simulation.liquidity`` 约束股数；返回 ``(shares, tag)``。"""
        return self.liquidity.apply_to_shares(
            planned_shares,
            tick_volume=bar_volume,
            floor_shares_fn=self.floor_shares,
            entity_id=entity_id,
        )

    def min_buy_shares(self, entity_id: str) -> int:
        lot = self.market_rules.resolve_lot_size(entity_id)
        return self.floor_shares(int(lot.min_lot), entity_id)

    def lot_step_for_stock(self, entity_id: str) -> int:
        """申报数量步长：主板/创业板 100，科创板/北证 1。"""
        lot = self.market_rules.resolve_lot_size(entity_id)
        return max(int(lot.lot_step or 1), 1)

    def size_sell_shares(
        self,
        *,
        remaining: int,
        initial_shares: int,
        exit_ratio: float,
        entity_id: str,
        is_last: bool,
    ) -> int:
        """纪律卖出股数：比例由资金层算，合法申报数量问 market profile。"""
        left = int(remaining)
        if left <= 0:
            return 0
        try:
            ratio = float(exit_ratio)
        except (TypeError, ValueError):
            ratio = 1.0
        if is_last or ratio >= 1.0 - 1e-12:
            return self.market_rules.floor_sell_quantity_for_stock(left, left, entity_id)
        initial = max(int(initial_shares or left), 1)
        planned = min(left, max(int(initial * max(ratio, 0.0)), 0))
        return self.market_rules.floor_sell_quantity_for_stock(
            planned, left, entity_id
        )

    def _equal_capital(self, account: Account, buy_price: float, entity_id: str) -> int:
        if float(account.cash) < self.per_trade_capital:
            return 0
        planned = self.floor_shares(int(self.per_trade_capital / buy_price), entity_id)
        return self._resolve_planned(
            planned_shares=planned,
            entity_id=entity_id,
            cash=min(float(account.cash), self.per_trade_capital),
            buy_price=buy_price,
        )

    def _equal_shares(self, account: Account, buy_price: float, entity_id: str) -> int:
        lot = self.market_rules.resolve_lot_size(entity_id)
        planned = self.floor_shares(
            int(lot.min_lot) * int(self.lots_per_trade), entity_id
        )
        return self._resolve_planned(
            planned_shares=planned,
            entity_id=entity_id,
            cash=float(account.cash),
            buy_price=buy_price,
        )

    def _kelly(
        self,
        account: Account,
        buy_price: float,
        entity_id: str,
        win_rate: Optional[float],
        payoff: Optional[float],
    ) -> int:
        if win_rate is None:
            return self._default_invest(account, buy_price, entity_id)
        f_raw = kelly_raw_fraction(win_rate, 1.0 if payoff is None else payoff)
        if f_raw <= 0:
            return 0
        scale = self.kelly_fraction if self.kelly_fraction > 0 else 1.0
        target_capital = f_raw * scale * float(account.cash)
        planned = self.floor_shares(int(target_capital / buy_price), entity_id)
        return self._resolve_planned(
            planned_shares=planned,
            entity_id=entity_id,
            cash=float(account.cash),
            buy_price=buy_price,
        )

    def _default_invest(self, account: Account, buy_price: float, entity_id: str) -> int:
        """没有已平仓样本时按 default_cash，否则按 default_shares。"""
        if self.default_cash > 0:
            budget = min(float(account.cash), self.default_cash)
            planned = self.floor_shares(int(budget / buy_price), entity_id)
            return self._resolve_planned(
                planned_shares=planned,
                entity_id=entity_id,
                cash=budget,
                buy_price=buy_price,
            )
        if self.default_shares > 0:
            planned = self.floor_shares(self.default_shares, entity_id)
            return self._resolve_planned(
                planned_shares=planned,
                entity_id=entity_id,
                cash=float(account.cash),
                buy_price=buy_price,
            )
        return 0

    def suggest_shares(
        self,
        account: Account,
        buy_price: float,
        entity_id: str,
        *,
        win_rate: Optional[float] = None,
        payoff: Optional[float] = None,
    ) -> int:
        """建议股数只按仓位公式折手，不掺佣金。实际下单仍走 ``calculate_shares_to_buy``。"""
        px = float(buy_price or 0.0)
        if px <= 0:
            return 0
        min_lot = self.min_buy_shares(entity_id)
        if self.mode == "equal_capital":
            planned = self.floor_shares(int(self.per_trade_capital / px), entity_id)
            return planned if planned >= min_lot else 0
        if self.mode == "equal_shares":
            lot = self.market_rules.resolve_lot_size(entity_id)
            planned = self.floor_shares(
                int(lot.min_lot) * int(self.lots_per_trade), entity_id
            )
            return planned if planned >= min_lot else 0
        if self.mode == "kelly":
            if win_rate is None:
                return self._suggest_default(px, entity_id, min_lot)
            f_raw = kelly_raw_fraction(win_rate, 1.0 if payoff is None else payoff)
            if f_raw <= 0:
                return 0
            scale = self.kelly_fraction if self.kelly_fraction > 0 else 1.0
            target_capital = f_raw * scale * float(account.cash)
            planned = self.floor_shares(int(target_capital / px), entity_id)
            return planned if planned >= min_lot else 0
        return 0

    def _suggest_default(self, buy_price: float, entity_id: str, min_lot: int) -> int:
        if self.default_cash > 0:
            planned = self.floor_shares(int(self.default_cash / buy_price), entity_id)
            return planned if planned >= min_lot else 0
        if self.default_shares > 0:
            planned = self.floor_shares(self.default_shares, entity_id)
            return planned if planned >= min_lot else 0
        return 0

    def _resolve_planned(
        self,
        *,
        planned_shares: int,
        entity_id: str,
        cash: float,
        buy_price: float,
    ) -> int:
        min_lot = self.min_buy_shares(entity_id)
        if planned_shares <= 0 or buy_price <= 0 or min_lot <= 0:
            return 0
        if self.fee_calculator.buy_total_cost(min_lot * buy_price) > cash:
            return 0
        fitted = self._fit_shares(
            planned_shares,
            cash=cash,
            buy_price=buy_price,
            entity_id=entity_id,
        )
        if fitted > 0:
            return fitted
        if self.skip_trade_when_insufficient:
            return 0
        return self._fit_shares(
            self._max_affordable_shares(cash, buy_price),
            cash=cash,
            buy_price=buy_price,
            entity_id=entity_id,
        )

    def _fit_shares(
        self,
        shares: int,
        *,
        cash: float,
        buy_price: float,
        entity_id: str,
    ) -> int:
        """从计划股数向下取整，直到含费用后仍买得起。"""
        min_lot = self.min_buy_shares(entity_id)
        step = self.lot_step_for_stock(entity_id)
        n = self.floor_shares(int(shares), entity_id)
        while n >= min_lot:
            if self.fee_calculator.buy_total_cost(n * buy_price) <= cash:
                return n
            overshoot = self.fee_calculator.buy_total_cost(n * buy_price) - cash
            drop = max(int(overshoot / buy_price) + 1, step)
            nxt = n - drop
            n = self.floor_shares(nxt, entity_id) if nxt >= min_lot else 0
        return 0

    def _max_affordable_shares(self, cash: float, buy_price: float) -> int:
        if cash <= 0 or buy_price <= 0:
            return 0
        rate = float(self.fee_calculator.commission_rate or 0.0) + float(
            self.fee_calculator.transfer_fee_rate or 0.0
        )
        min_c = float(self.fee_calculator.min_commission or 0.0)
        cap_rate = cash / (1.0 + rate) if rate > 0 else cash
        cap_min = cash - min_c
        amount = min(cap_rate, cap_min)
        return int(amount / buy_price) if amount > 0 else 0


def kelly_raw_fraction(win_rate: float, payoff: float) -> float:
    """凯利仓位 f = p - (1-p)/b。没有亏损样本时 f = p。"""
    p = min(max(float(win_rate), 0.0), 1.0)
    if payoff == float("inf"):
        return p
    b = float(payoff)
    if b <= 0:
        return 0.0
    return p - (1.0 - p) / b


def payoff_ratio(rois: Sequence[float]) -> Tuple[float, float]:
    """已平仓 ROI 列表 → ``(胜率, 盈亏比)``。盈亏比是平均盈利 / 平均亏损绝对值。"""
    sample = [float(item) for item in rois]
    if not sample:
        return 0.0, 0.0
    wins = [item for item in sample if item > 0]
    losses = [item for item in sample if item < 0]
    p = len(wins) / float(len(sample))
    if wins and not losses:
        return p, float("inf")
    if not wins or not losses:
        return p, 0.0
    b = (sum(wins) / len(wins)) / (sum(-item for item in losses) / len(losses))
    return p, b


__all__ = ["AllocationStrategy", "kelly_raw_fraction", "payoff_ratio"]
