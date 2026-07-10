"""Opportunity data class (minimal version for compatibility)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Opportunity:
    """Opportunity data class (minimal version).

    TODO: 后续完善完整Opportunity逻辑（包括投资状态、tradability等）
    """
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
    buy_price: float = 0.0
    sell_price: float = 0.0
    target_sell_price: float = 0.0
    stop_loss_price: float = 0.0
    max_holding_days: int = 0
    sell_reason: str = ""
    outcome: str = ""
    completed_targets: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        return {
            'stock': self.stock,
            'record_of_today': self.record_of_today,
            'extra_fields': self.extra_fields,
            'opportunity_id': self.opportunity_id,
            'stock_id': self.stock_id,
            'stock_name': self.stock_name,
            'strategy_name': self.strategy_name,
            'strategy_version': self.strategy_version,
            'scan_date': self.scan_date,
            'trigger_date': self.trigger_date,
            'trigger_price': self.trigger_price,
            'buy_price': self.buy_price,
            'sell_price': self.sell_price,
            'target_sell_price': self.target_sell_price,
            'stop_loss_price': self.stop_loss_price,
            'max_holding_days': self.max_holding_days,
            'sell_reason': self.sell_reason,
            'outcome': self.outcome,
            'completed_targets': list(self.completed_targets),
        }


__all__ = ['Opportunity']