#!/usr/bin/env python3
"""Opportunity Model - 投资机会模型"""

from dataclasses import asdict, dataclass
from datetime import datetime
import logging
from typing import Any, Dict, Optional

from core.modules.strategy.enums import OpportunityStatus

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

    def __post_init__(self):
        if not self.stock_id and self.stock:
            self.stock_id = self.stock.get("id", "")
        if not self.stock_name and self.stock:
            self.stock_name = self.stock.get("name", "")
        if not self.trigger_date and self.record_of_today:
            self.trigger_date = self.record_of_today.get("date", "")
        if not self.trigger_price and self.record_of_today:
            self.trigger_price = self.record_of_today.get("close", 0.0)
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

    def settle(self, last_kline: Dict[str, Any], reason: str = "backtest_end"):
        current_price = last_kline["close"]
        current_date = last_kline["date"]
        price_return = (current_price - self.trigger_price) / self.trigger_price
        self._settle(current_date, current_price, reason, price_return, sell_ratio=1.0)

    def check_targets(
        self,
        current_kline: Dict[str, Any],
        goal_config: Dict[str, Any],
    ) -> bool:
        current_price = current_kline["close"]
        current_date = current_kline["date"]

        holding_days = self._calculate_holding_days(self.trigger_date, current_date)
        price_return = (current_price - self.trigger_price) / self.trigger_price

        self.max_price = max(self.max_price or 0, current_price)
        self.min_price = min(self.min_price or float("inf"), current_price)

        expiration_config = goal_config.get("expiration", {})
        if expiration_config:
            fixed_window_in_days = expiration_config.get("fixed_window_in_days", 0)
            if fixed_window_in_days > 0 and holding_days >= fixed_window_in_days:
                self._settle(
                    current_date,
                    current_price,
                    "expiration",
                    price_return,
                    sell_ratio=1.0,
                )
                return True

        if self.protect_loss_active:
            protect_loss_config = goal_config.get("protect_loss", {})
            protect_ratio = protect_loss_config.get("ratio", 0)
            if price_return <= protect_ratio:
                self._settle(
                    current_date,
                    current_price,
                    "protect_loss",
                    price_return,
                    sell_ratio=1.0,
                )
                return True

        if self.dynamic_loss_active:
            dynamic_loss_config = goal_config.get("dynamic_loss", {})
            dynamic_ratio = dynamic_loss_config.get("ratio", -0.1)
            if not self.dynamic_loss_highest:
                self.dynamic_loss_highest = self.trigger_price
            self.dynamic_loss_highest = max(self.dynamic_loss_highest, current_price)
            dynamic_threshold = (
                current_price - self.dynamic_loss_highest
            ) / self.dynamic_loss_highest
            if dynamic_threshold <= dynamic_ratio:
                self._settle(
                    current_date,
                    current_price,
                    "dynamic_loss",
                    price_return,
                    sell_ratio=1.0,
                )
                return True

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
                    self._settle(
                        current_date,
                        current_price,
                        reason,
                        price_return,
                        sell_ratio=1.0,
                    )
                    return True

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
                    self._settle(
                        current_date,
                        current_price,
                        reason,
                        price_return,
                        sell_ratio=1.0,
                    )
                    return True
                else:
                    if not self.completed_targets:
                        self.completed_targets = []
                    sell_ratio = stage.get("sell_ratio", 1.0)
                    profit = current_price - self.trigger_price
                    weighted_profit = profit * sell_ratio
                    self.completed_targets.append(
                        {
                            "date": current_date,
                            "price": current_price,
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
        profit = sell_price - self.trigger_price
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
        self.roi = total_weighted_profit / self.trigger_price if self.trigger_price > 0 else 0.0
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
            self.trigger_price = self.record_of_today.get("close", 0.0)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Opportunity":
        return cls(**data)
