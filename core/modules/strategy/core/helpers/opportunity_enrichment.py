"""Opportunity 触发字段补全（从 settings 推导 goal 价位等）。"""
from __future__ import annotations

from typing import Any, Dict, Optional

from core.modules.strategy.core.engines.shared.data_classes import Opportunity


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
        opportunity.opportunity_id = str(opportunity_index)
        opportunity.stock_id = stock_id
        opportunity.strategy_name = strategy_name
        opportunity.trigger_date = trigger_date
        opportunity.scan_date = trigger_date
        opportunity.trigger_price = float(trigger_price)

        if opportunity.stock:
            opportunity.stock = {**stock_info, **opportunity.stock}
        else:
            opportunity.stock = dict(stock_info)
        opportunity.stock_name = str(stock_info.get("name") or stock_id)

        goal = settings.get("goal") if isinstance(settings.get("goal"), dict) else {}
        stop_ratio = OpportunityEnricher._first_stage_ratio(goal.get("stop_loss"))
        if stop_ratio is not None and trigger_price > 0:
            opportunity.stop_loss_price = round(trigger_price * (1.0 + stop_ratio), 6)

        profit_ratio = OpportunityEnricher._first_stage_ratio(goal.get("take_profit"))
        if profit_ratio is not None and trigger_price > 0:
            opportunity.target_sell_price = round(trigger_price * (1.0 + profit_ratio), 6)

        simulation = settings.get("simulation") if isinstance(settings.get("simulation"), dict) else {}
        max_days = simulation.get("max_holding_days")
        if isinstance(max_days, int) and max_days > 0:
            opportunity.max_holding_days = max_days

        return opportunity

    @staticmethod
    def _first_stage_ratio(block: Any) -> Optional[float]:
        if not isinstance(block, dict):
            return None
        stages = block.get("stages")
        if not isinstance(stages, list) or not stages:
            return None
        first = stages[0]
        if not isinstance(first, dict) or "ratio" not in first:
            return None
        try:
            return float(first["ratio"])
        except (TypeError, ValueError):
            return None


__all__ = ["OpportunityEnricher"]
