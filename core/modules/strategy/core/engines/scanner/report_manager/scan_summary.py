"""Scanner 扫描汇总（纯数据）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.modules.strategy.core.engines.scanner.helpers import opportunity_enter_at_limit
from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity


@dataclass
class ScanSummary:
    """一次扫描的全局汇总。"""

    total_opportunities: int = 0
    total_stocks: int = 0
    stocks_with_opportunities: List[str] = field(default_factory=list)
    at_limit_up_count: int = 0

    @classmethod
    def from_opportunities(cls, opportunities: List[Opportunity]) -> "ScanSummary":
        if not opportunities:
            return cls()
        stocks = {opp.stock_id for opp in opportunities if opp.stock_id}
        at_limit = sum(
            1 for opp in opportunities if opportunity_enter_at_limit(opp) is True
        )
        return cls(
            total_opportunities=len(opportunities),
            total_stocks=len(stocks),
            stocks_with_opportunities=sorted(stocks),
            at_limit_up_count=at_limit,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_opportunities": self.total_opportunities,
            "total_stocks": self.total_stocks,
            "stocks_with_opportunities": list(self.stocks_with_opportunities),
            "at_limit_up_count": self.at_limit_up_count,
        }


__all__ = ["ScanSummary"]
