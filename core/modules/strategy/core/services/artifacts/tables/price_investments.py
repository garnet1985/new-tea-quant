"""价格层 ``*_investments.csv`` 行模型（无 IO）。"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, ClassVar, Dict, List, Sequence


@dataclass
class PriceInvestmentRow:
    """价格层单笔投资记录（成交回放后）。

    ``enter_price`` / ``exit_price`` 为 qfq（K 线标注）；``*_hfq`` 为后复权对账价。
    ``roi`` 为 hfq 收益：无顺延时等于枚举 ``weighted_roi``，跌停顺延后按 hfq 重算。
    ``completed_goals`` 仅内存：已成交目标（对应 ``goal_achievements.csv``），不写入 investments CSV。
    """

    opportunity_id: str = ""
    enter_date: str = ""
    enter_price: float = 0.0
    enter_price_hfq: float = 0.0
    exit_date: str = ""
    exit_price: float = 0.0
    exit_price_hfq: float = 0.0
    roi: float = 0.0
    holding_days: int = 0
    holding_trading_days: int = 0
    exit_reason: str = ""
    skip_reason: str = ""
    lifecycle: str = ""
    result: str = ""
    completed_goals: List[Dict[str, Any]] = field(default_factory=list)

    COLUMN_ORDER: ClassVar[Sequence[str]] = (
        "opportunity_id",
        "enter_date",
        "enter_price",
        "enter_price_hfq",
        "exit_date",
        "exit_price",
        "exit_price_hfq",
        "roi",
        "holding_days",
        "holding_trading_days",
        "exit_reason",
        "skip_reason",
        "lifecycle",
        "result",
    )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data.pop("completed_goals", None)
        return data

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "PriceInvestmentRow":
        data = raw or {}
        return cls(
            opportunity_id=str(data.get("opportunity_id") or "").strip(),
            enter_date=str(data.get("enter_date") or "").strip(),
            enter_price=cls.as_float(data.get("enter_price")),
            enter_price_hfq=cls.as_float(data.get("enter_price_hfq")),
            exit_date=str(data.get("exit_date") or "").strip(),
            exit_price=cls.as_float(data.get("exit_price")),
            exit_price_hfq=cls.as_float(data.get("exit_price_hfq")),
            roi=cls.as_float(data.get("roi")),
            holding_days=cls.as_int(data.get("holding_days")),
            holding_trading_days=cls.as_int(data.get("holding_trading_days")),
            exit_reason=str(data.get("exit_reason") or "").strip(),
            skip_reason=str(data.get("skip_reason") or "").strip(),
            lifecycle=str(data.get("lifecycle") or "").strip(),
            result=str(data.get("result") or "").strip(),
        )

    @staticmethod
    def as_float(value: Any, default: float = 0.0) -> float:
        if value is None or value == "":
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def as_int(value: Any, default: int = 0) -> int:
        if value is None or value == "":
            return default
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


__all__ = ["PriceInvestmentRow"]
