"""Opportunity 触发字段补全（从 settings 推导 goal 价位等）。"""
from __future__ import annotations

from typing import Any, Dict

from core.modules.strategy.core.engines.shared.data_classes import Opportunity
from core.modules.strategy.core.helpers.goal_config import GoalConfig


class OpportunityEnricher:
    """枚举阶段 Opportunity 标准字段补全。"""

    @staticmethod
    def apply_trigger_fields(
        opportunity: Opportunity,
        *,
        settings: Dict[str, Any],
        strategy_name: str,
        stock_id: str,
        stock_info: Dict[str, Any],
        trigger_date: str,
        trigger_price: float,
        opportunity_index: int,
    ) -> Opportunity:
        if trigger_price <= 0:
            raise ValueError("trigger_price 须 > 0")

        opportunity.opportunity_id = str(opportunity_index)
        opportunity.stock_id = stock_id
        opportunity.strategy_name = strategy_name
        opportunity.trigger_date = trigger_date
        opportunity.scan_date = trigger_date
        opportunity.trigger_price = float(trigger_price)
        opportunity.buy_price = float(trigger_price)

        if opportunity.stock:
            opportunity.stock = {**stock_info, **opportunity.stock}
        else:
            opportunity.stock = dict(stock_info)
        opportunity.stock_name = str(stock_info.get("name") or stock_id)

        goal = GoalConfig.from_settings(settings)
        if goal.stop_loss is not None:
            opportunity.stop_loss_price = goal.exit_price(goal.stop_loss, trigger_price)
        if goal.take_profit is not None:
            opportunity.target_sell_price = goal.exit_price(goal.take_profit, trigger_price)

        simulation = settings.get("simulation")
        if simulation is not None:
            if not isinstance(simulation, dict):
                raise ValueError("settings.simulation 须为 dict")
            if "max_holding_days" in simulation:
                max_days = simulation["max_holding_days"]
                if not isinstance(max_days, int) or max_days < 0:
                    raise ValueError("settings.simulation.max_holding_days 须为非负整数")
                if max_days > 0:
                    opportunity.max_holding_days = max_days

        return opportunity


__all__ = ["OpportunityEnricher"]
