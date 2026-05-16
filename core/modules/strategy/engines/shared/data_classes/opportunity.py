#!/usr/bin/env python3
"""Opportunity Model - 投资机会模型"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import datetime
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from core.modules.strategy.enums import OpportunityStatus
from core.modules.strategy.engines.shared.helpers.simulation_pricing import (
    apply_sell_slippage,
    monitor_bar_price,
    trade_price_defers_to_next_session,
    trade_theoretical_price_on_bar,
)

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
        StrategySimulationSettings,
    )

logger = logging.getLogger(__name__)


@dataclass
class Opportunity:
    stock: Dict[str, Any]
    record_of_today: Dict[str, Any]
    extra_fields: Optional[Dict[str, Any]] = None
    opportunity_id: str = ""
    stock_id: str = ""
    stock_name: str = ""
    strategy_name: str = ""
    strategy_version: str = ""
    scan_date: str = ""
    trigger_date: str = ""
    trigger_price: float = 0.0
    """信号日参考价（通常为当日 close），与真实买入成本分离。"""
    buy_price: float = 0.0
    """真实买入成本（含滑点）；清算与止盈止损比例以该价为分母。"""
    buy_date: str = ""
    """真实成交日；可与 ``trigger_date``（信号日）不同。"""
    buy_fill_pending: bool = False
    """``next_open`` 买入：信号日置 True，下一交易日 open 成交后置 False。"""
    pending_exit: Optional[Dict[str, Any]] = None
    """``next_open`` 卖出：触发日写入，下一交易日 open 成交。"""
    sell_date: Optional[str] = None
    sell_price: Optional[float] = None
    sell_reason: Optional[str] = None
    price_return: Optional[float] = None
    holding_days: Optional[int] = None
    max_price: Optional[float] = None
    min_price: Optional[float] = None
    max_drawdown: Optional[float] = None
    tracking: Optional[Dict[str, Any]] = None
    protect_loss_active: bool = False
    dynamic_loss_active: bool = False
    dynamic_loss_highest: Optional[float] = None
    triggered_stop_loss_idx: int = -1
    triggered_take_profit_idx: int = -1
    roi: Optional[float] = None
    completed_targets: Optional[list] = None
    status: str = "active"
    expired_date: Optional[str] = None
    expired_reason: Optional[str] = None
    config_hash: str = ""
    created_at: str = ""
    updated_at: str = ""
    metadata: Dict[str, Any] = None

    def _cost_basis(self) -> float:
        if self.buy_price and self.buy_price > 0:
            return float(self.buy_price)
        return float(self.trigger_price or 0.0)

    def _exit_price(
        self,
        sim: "StrategySimulationSettings",
        bar: Dict[str, Any],
    ) -> Optional[float]:
        raw = trade_theoretical_price_on_bar(
            sim.sell_price_model,
            side="sell",
            bar=bar,
        )
        if raw is None:
            return None
        return apply_sell_slippage(raw, sim.slippage_sell_bps)

    def _settle_on_bar(
        self,
        sim: "StrategySimulationSettings",
        bar: Dict[str, Any],
        reason: str,
        *,
        sell_ratio: float = 1.0,
    ) -> bool:
        exit_px = self._exit_price(sim, bar)
        if exit_px is None:
            return False
        basis = self._cost_basis()
        current_date = bar["date"]
        price_return = (exit_px - basis) / basis if basis > 0 else 0.0
        self._settle(current_date, exit_px, reason, price_return, sell_ratio=sell_ratio)
        return True

    def _defer_exit(self, reason: str, *, sell_ratio: float = 1.0) -> bool:
        self.pending_exit = {"reason": reason, "sell_ratio": sell_ratio}
        return True

    def _request_exit(
        self,
        sim: "StrategySimulationSettings",
        bar: Dict[str, Any],
        reason: str,
        *,
        sell_ratio: float = 1.0,
    ) -> bool:
        if trade_price_defers_to_next_session(sim.sell_price_model):
            return self._defer_exit(reason, sell_ratio=sell_ratio)
        return self._settle_on_bar(sim, bar, reason, sell_ratio=sell_ratio)

    def execute_pending_exit(
        self,
        sim: "StrategySimulationSettings",
        bar: Dict[str, Any],
    ) -> bool:
        if not self.pending_exit:
            return False
        pe = self.pending_exit
        self.pending_exit = None
        return self._settle_on_bar(
            sim,
            bar,
            str(pe.get("reason") or "exit"),
            sell_ratio=float(pe.get("sell_ratio") or 1.0),
        )

    def __post_init__(self):
        if not self.stock_id and self.stock:
            self.stock_id = self.stock.get("id", "")
        if not self.stock_name and self.stock:
            self.stock_name = self.stock.get("name", "")
        if not self.trigger_date and self.record_of_today:
            self.trigger_date = self.record_of_today.get("date", "")
        if not self.trigger_price and self.record_of_today:
            self.trigger_price = float(self.record_of_today.get("close") or 0.0)
        if not self.buy_fill_pending:
            if (not self.buy_price or self.buy_price <= 0) and self.trigger_price > 0:
                self.buy_price = float(self.trigger_price)
            if not self.buy_date and self.trigger_date:
                self.buy_date = str(self.trigger_date)
        if self.stock:
            if "id" not in self.stock and self.stock_id:
                self.stock["id"] = self.stock_id
            if "name" not in self.stock and self.stock_name:
                self.stock["name"] = self.stock_name
            self.stock.setdefault("industry", "")
            self.stock.setdefault("type", "")
            self.stock.setdefault("exchange_center", "")
        if self.extra_fields is None:
            self.extra_fields = {}
        if self.metadata is None:
            self.metadata = {}
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()

    def is_valid(self) -> bool:
        return self.status == OpportunityStatus.ACTIVE.value

    def is_closed(self) -> bool:
        return self.status == OpportunityStatus.CLOSED.value

    def calculate_annual_return(self) -> float:
        if not self.price_return or not self.holding_days:
            return 0.0
        return self.price_return * (250 / self.holding_days)

    def settle(
        self,
        sim: "StrategySimulationSettings",
        last_kline: Dict[str, Any],
        reason: str = "backtest_end",
    ) -> None:
        if self.pending_exit and trade_price_defers_to_next_session(sim.sell_price_model):
            pe = self.pending_exit
            self.pending_exit = None
            self._settle_on_bar(
                sim,
                last_kline,
                str(pe.get("reason") or reason),
                sell_ratio=float(pe.get("sell_ratio") or 1.0),
            )
            return
        self._settle_on_bar(sim, last_kline, reason, sell_ratio=1.0)

    def check_targets(
        self,
        sim: "StrategySimulationSettings",
        current_kline: Dict[str, Any],
        goal_config: Dict[str, Any],
    ) -> bool:
        current_price = monitor_bar_price(current_kline, sim.monitor_price_model)
        current_date = current_kline["date"]
        basis = self._cost_basis()

        # expiration / 持仓天数：自真实买入日计；``next_open`` 成交前未建仓，不会进入本方法
        holding_days = self._calculate_holding_days(self.buy_date or self.trigger_date, current_date)
        price_return = (current_price - basis) / basis if basis > 0 else 0.0

        self.max_price = max(self.max_price or 0, current_price)
        self.min_price = min(self.min_price or float("inf"), current_price)

        expiration_config = goal_config.get("expiration", {})
        if expiration_config:
            fixed_window_in_days = expiration_config.get("fixed_window_in_days", 0)
            if fixed_window_in_days > 0 and holding_days >= fixed_window_in_days:
                if self._request_exit(sim, current_kline, "expiration", sell_ratio=1.0):
                    return self.pending_exit is None

        if self.protect_loss_active:
            protect_loss_config = goal_config.get("protect_loss", {})
            protect_ratio = protect_loss_config.get("ratio", 0)
            if price_return <= protect_ratio:
                if self._request_exit(sim, current_kline, "protect_loss", sell_ratio=1.0):
                    return self.pending_exit is None

        if self.dynamic_loss_active:
            dynamic_loss_config = goal_config.get("dynamic_loss", {})
            dynamic_ratio = dynamic_loss_config.get("ratio", -0.1)
            if not self.dynamic_loss_highest:
                self.dynamic_loss_highest = basis
            self.dynamic_loss_highest = max(self.dynamic_loss_highest, current_price)
            dynamic_threshold = (
                current_price - self.dynamic_loss_highest
            ) / self.dynamic_loss_highest if self.dynamic_loss_highest else 0.0
            if dynamic_threshold <= dynamic_ratio:
                if self._request_exit(sim, current_kline, "dynamic_loss", sell_ratio=1.0):
                    return self.pending_exit is None

        stop_loss_stages = goal_config.get("stop_loss", {}).get("stages", [])
        for idx, stage in enumerate(stop_loss_stages):
            if idx <= self.triggered_stop_loss_idx:
                continue
            stage_ratio = stage.get("ratio", 0)
            if price_return <= stage_ratio:
                self.triggered_stop_loss_idx = idx
                if stage.get("close_invest", False):
                    stage_name = stage.get("name")
                    if stage_name:
                        reason = stage_name
                    else:
                        ratio_percent = int(stage_ratio * 100)
                        reason = f"stop_loss_{ratio_percent}%"
                    if self._request_exit(sim, current_kline, reason, sell_ratio=1.0):
                        return self.pending_exit is None

        take_profit_stages = goal_config.get("take_profit", {}).get("stages", [])
        for idx, stage in enumerate(take_profit_stages):
            if idx <= self.triggered_take_profit_idx:
                continue
            stage_ratio = stage.get("ratio", 0)
            if price_return >= stage_ratio:
                self.triggered_take_profit_idx = idx
                actions = stage.get("actions", [])
                if "set_protect_loss" in actions:
                    self.protect_loss_active = True
                if "set_dynamic_loss" in actions:
                    self.dynamic_loss_active = True
                    self.dynamic_loss_highest = current_price

                stage_name = stage.get("name")
                if stage_name:
                    reason = stage_name
                else:
                    ratio_percent = int(stage_ratio * 100)
                    reason = f"take_profit_{ratio_percent}%"

                if stage.get("close_invest", False):
                    if self._request_exit(sim, current_kline, reason, sell_ratio=1.0):
                        return self.pending_exit is None
                if not self.completed_targets:
                    self.completed_targets = []
                sell_ratio = stage.get("sell_ratio", 1.0)
                if trade_price_defers_to_next_session(sim.sell_price_model):
                    self._defer_exit(reason, sell_ratio=sell_ratio)
                    continue
                exit_px = self._exit_price(sim, current_kline)
                if exit_px is None:
                    continue
                profit = exit_px - basis
                weighted_profit = profit * sell_ratio
                self.completed_targets.append(
                    {
                        "date": current_date,
                        "price": exit_px,
                        "reason": reason,
                        "roi": price_return,
                        "sell_ratio": sell_ratio,
                        "profit": profit,
                        "weighted_profit": weighted_profit,
                    }
                )

        return False

    def _calculate_holding_days(self, start_date: str, end_date: str) -> int:
        try:
            start = datetime.strptime(start_date, "%Y%m%d")
            end = datetime.strptime(end_date, "%Y%m%d")
            return (end - start).days
        except Exception:
            return 0

    def _settle(
        self,
        sell_date: str,
        sell_price: float,
        sell_reason: str,
        roi: float,
        sell_ratio: float = 1.0,
    ):
        self.sell_date = sell_date
        self.sell_price = sell_price
        self.sell_reason = sell_reason
        if not self.completed_targets:
            self.completed_targets = []
        basis = self._cost_basis()
        profit = sell_price - basis
        weighted_profit = profit * sell_ratio
        self.completed_targets.append(
            {
                "date": sell_date,
                "price": sell_price,
                "reason": sell_reason,
                "roi": roi,
                "sell_ratio": sell_ratio,
                "profit": profit,
                "weighted_profit": weighted_profit,
            }
        )
        total_weighted_profit = sum(
            target.get("weighted_profit", 0) for target in self.completed_targets
        )
        self.roi = total_weighted_profit / basis if basis > 0 else 0.0
        total_sell_ratio = sum(target.get("sell_ratio", 0) for target in self.completed_targets)
        is_fully_completed = total_sell_ratio >= 1.0
        if is_fully_completed:
            self.status = (
                OpportunityStatus.WIN.value
                if self.roi > 0
                else OpportunityStatus.LOSS.value
            )
        else:
            self.status = OpportunityStatus.OPEN.value

    def enrich_from_framework(
        self,
        strategy_name: str,
        strategy_version: str = "1.0",
        opportunity_id: Optional[str] = None,
    ):
        self.strategy_name = strategy_name
        self.strategy_version = strategy_version
        self.scan_date = datetime.now().strftime("%Y%m%d")
        if not self.opportunity_id:
            if opportunity_id:
                self.opportunity_id = opportunity_id
            else:
                import uuid

                logger.warning("Opportunity ID 未设置，使用 UUID 临时方案")
                self.opportunity_id = str(uuid.uuid4())
        if not self.stock_id and self.stock:
            self.stock_id = self.stock.get("id", "")
        if not self.stock_name and self.stock:
            self.stock_name = self.stock.get("name", "")
        if not self.trigger_date and self.record_of_today:
            self.trigger_date = self.record_of_today.get("date", "")
        if not self.trigger_price and self.record_of_today:
            self.trigger_price = float(self.record_of_today.get("close") or 0.0)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Opportunity":
        raw = dict(data or {})

        def _to_float(v: Any, default: float = 0.0) -> float:
            if v is None or v == "":
                return default
            if isinstance(v, (int, float)):
                return float(v)
            try:
                return float(str(v).strip())
            except (TypeError, ValueError):
                return default

        def _to_opt_float(v: Any) -> Optional[float]:
            if v is None or v == "":
                return None
            if isinstance(v, (int, float)):
                return float(v)
            try:
                return float(str(v).strip())
            except (TypeError, ValueError):
                return None

        for key in ("trigger_price", "buy_price"):
            if key in raw:
                raw[key] = _to_float(raw.get(key), 0.0)
        for key in ("sell_price", "price_return", "max_price", "min_price", "roi"):
            if key in raw:
                raw[key] = _to_opt_float(raw.get(key))
        allowed = {f.name for f in fields(cls)}
        raw = {k: v for k, v in raw.items() if k in allowed}
        return cls(**raw)
