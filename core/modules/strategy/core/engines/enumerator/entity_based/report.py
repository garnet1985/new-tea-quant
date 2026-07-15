"""DEPRECATED — 请使用 ``shared.report_manager.ReportManager``。

历史 template 数据类；``shared.services.statistics`` 仍引用 ``EnumeratorReportTemplate``。
新 enum 路径不走本模块。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EnumeratorReportTemplate:
    """旧 enumerator report template（未接入当前 ReportManager）。"""

    total_opportunities: int = 0
    total_stocks: int = 0
    trigger_stocks: int = 0
    completed_count: int = 0
    unfinished_count: int = 0
    stock_rows: List[Dict[str, Any]] = field(default_factory=list)
    tradability_stats: Optional[Dict[str, Any]] = None
    percentile_stats: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_opportunities": self.total_opportunities,
            "total_stocks": self.total_stocks,
            "trigger_stocks": self.trigger_stocks,
            "completed_count": self.completed_count,
            "unfinished_count": self.unfinished_count,
            "stock_rows": list(self.stock_rows),
            "tradability_stats": dict(self.tradability_stats or {}),
            "percentile_stats": dict(self.percentile_stats or {}),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "EnumeratorReportTemplate":
        return cls(
            total_opportunities=payload.get("total_opportunities", 0),
            total_stocks=payload.get("total_stocks", 0),
            trigger_stocks=payload.get("trigger_stocks", 0),
            completed_count=payload.get("completed_count", 0),
            unfinished_count=payload.get("unfinished_count", 0),
            stock_rows=payload.get("stock_rows", []),
            tradability_stats=payload.get("tradability_stats"),
            percentile_stats=payload.get("percentile_stats"),
        )


@dataclass
class PriceFactorReportTemplate:
    """旧 price-factor report template（未接入当前 ReportManager）。"""

    total_simulations: int = 0
    completed_count: int = 0
    unfinished_count: int = 0
    avg_roi: float = 0.0
    avg_holding_days: float = 0.0
    stock_rows: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_simulations": self.total_simulations,
            "completed_count": self.completed_count,
            "unfinished_count": self.unfinished_count,
            "avg_roi": self.avg_roi,
            "avg_holding_days": self.avg_holding_days,
            "stock_rows": list(self.stock_rows),
        }


@dataclass
class PortfolioReportTemplate:
    """旧 portfolio report template（未接入当前 ReportManager）。"""

    total_equity: float = 0.0
    stock_rows: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_equity": self.total_equity,
            "stock_rows": list(self.stock_rows),
        }


__all__ = [
    "EnumeratorReportTemplate",
    "PriceFactorReportTemplate",
    "PortfolioReportTemplate",
]
