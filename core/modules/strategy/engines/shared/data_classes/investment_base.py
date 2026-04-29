#!/usr/bin/env python3
"""Shared investment base classes."""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any, Dict, Literal, Optional


@dataclass
class BaseInvestment(ABC):
    """投资基类（统一接口）"""

    investment_id: str
    opportunity_id: str
    stock_id: str
    buy_date: str
    buy_price: float
    stock_name: str = ""
    sell_date: Optional[str] = None
    sell_price: Optional[float] = None
    profit: float = 0.0
    roi: float = 0.0
    holding_days: int = 0
    status: Literal["open", "closed", "win", "loss"] = "open"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    @abstractmethod
    def from_source(cls, source: Any) -> "BaseInvestment":
        raise NotImplementedError
