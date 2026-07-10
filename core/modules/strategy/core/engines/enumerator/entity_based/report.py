"""Enumerator report data class layer."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class EnumeratorReportTemplate:
    """Enumerator report template (data class layer).

    定义enumerator report的数据结构（模版），不包含统计逻辑。

    TODO: 后续完善完整的report template（包括tradability统计、percentile等）。
    """
    total_opportunities: int = 0
    total_stocks: int = 0
    trigger_stocks: int = 0
    completed_count: int = 0
    unfinished_count: int = 0
    stock_rows: List[Dict[str, Any]] = field(default_factory=list)

    # 扩展字段（后续完善）
    tradability_stats: Optional[Dict[str, Any]] = None
    percentile_stats: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        return {
            'total_opportunities': self.total_opportunities,
            'total_stocks': self.total_stocks,
            'trigger_stocks': self.trigger_stocks,
            'completed_count': self.completed_count,
            'unfinished_count': self.unfinished_count,
            'stock_rows': list(self.stock_rows),
            'tradability_stats': dict(self.tradability_stats or {}),
            'percentile_stats': dict(self.percentile_stats or {}),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "EnumeratorReportTemplate":
        """Create from dict.

        Args:
            payload: payload dict

        Returns:
            EnumeratorReportTemplate实例
        """
        return cls(
            total_opportunities=payload.get('total_opportunities', 0),
            total_stocks=payload.get('total_stocks', 0),
            trigger_stocks=payload.get('trigger_stocks', 0),
            completed_count=payload.get('completed_count', 0),
            unfinished_count=payload.get('unfinished_count', 0),
            stock_rows=payload.get('stock_rows', []),
            tradability_stats=payload.get('tradability_stats'),
            percentile_stats=payload.get('percentile_stats'),
        )


@dataclass
class PriceFactorReportTemplate:
    """Price factor report template (data class layer).

    定义price factor report的数据结构（模版），不包含统计逻辑。

    TODO: 后续完善完整的report template。
    """
    total_simulations: int = 0
    completed_count: int = 0
    unfinished_count: int = 0
    avg_roi: float = 0.0
    avg_holding_days: float = 0.0
    stock_rows: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        return {
            'total_simulations': self.total_simulations,
            'completed_count': self.completed_count,
            'unfinished_count': self.unfinished_count,
            'avg_roi': self.avg_roi,
            'avg_holding_days': self.avg_holding_days,
            'stock_rows': list(self.stock_rows),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "PriceFactorReportTemplate":
        """Create from dict."""
        return cls(
            total_simulations=payload.get('total_simulations', 0),
            completed_count=payload.get('completed_count', 0),
            unfinished_count=payload.get('unfinished_count', 0),
            avg_roi=payload.get('avg_roi', 0.0),
            avg_holding_days=payload.get('avg_holding_days', 0.0),
            stock_rows=payload.get('stock_rows', []),
        )


@dataclass
class PortfolioReportTemplate:
    """Portfolio report template (data class layer).

    定义portfolio report的数据结构（模版），不包含统计逻辑。

    TODO: 后续完善完整的report template。
    """
    total_portfolios: int = 0
    completed_count: int = 0
    unfinished_count: int = 0
    avg_roi: float = 0.0
    avg_sharpe_ratio: float = 0.0
    portfolio_rows: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        return {
            'total_portfolios': self.total_portfolios,
            'completed_count': self.completed_count,
            'unfinished_count': self.unfinished_count,
            'avg_roi': self.avg_roi,
            'avg_sharpe_ratio': self.avg_sharpe_ratio,
            'portfolio_rows': list(self.portfolio_rows),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "PortfolioReportTemplate":
        """Create from dict."""
        return cls(
            total_portfolios=payload.get('total_portfolios', 0),
            completed_count=payload.get('completed_count', 0),
            unfinished_count=payload.get('unfinished_count', 0),
            avg_roi=payload.get('avg_roi', 0.0),
            avg_sharpe_ratio=payload.get('avg_sharpe_ratio', 0.0),
            portfolio_rows=payload.get('portfolio_rows', []),
        )


__all__ = [
    'EnumeratorReportTemplate',
    'PriceFactorReportTemplate',
    'PortfolioReportTemplate',
]