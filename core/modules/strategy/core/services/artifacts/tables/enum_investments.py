"""价格层 ``*_goal_achievements.csv`` 行模型（无 IO；读写见 PriceFactorStore）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Dict, Tuple

from core.modules.strategy.core.helpers.coerce import ValueCoerce


@dataclass
class GoalAchievementRow:
    """单笔已成交目标 → goal_achievements.csv 行。

    边界:
    - 负责: CSV 行互转
    - 不负责: 文件 IO（见 PriceFactorStore）
    - 调用方: PriceFactorStore / BFF 价格层标注
    """

    investment_id: str = ""
    goal_name: str = ""
    date: str = ""
    price: float = 0.0
    price_raw: float = 0.0
    price_hfq: float = 0.0
    exit_ratio: float = 0.0
    profit: float = 0.0
    weighted_profit: float = 0.0
    reason: str = ""
    roi: float = 0.0

    COLUMN_ORDER: ClassVar[Tuple[str, ...]] = (
        "investment_id",
        "goal_name",
        "date",
        "price",
        "price_raw",
        "price_hfq",
        "exit_ratio",
        "profit",
        "weighted_profit",
        "reason",
        "roi",
    )

    def to_csv_row(self) -> Dict[str, Any]:
        return {
            "investment_id": self.investment_id,
            "goal_name": self.goal_name,
            "date": self.date,
            "price": self.price,
            "price_raw": self.price_raw,
            "price_hfq": self.price_hfq,
            "exit_ratio": self.exit_ratio,
            "profit": self.profit,
            "weighted_profit": self.weighted_profit,
            "reason": self.reason,
            "roi": self.roi,
        }

    @classmethod
    def from_csv_row(cls, raw: Dict[str, Any]) -> "GoalAchievementRow":
        data = raw or {}
        return cls(
            investment_id=_require_non_empty(data.get("investment_id"), "investment_id"),
            goal_name=_require_non_empty(data.get("goal_name"), "goal_name"),
            date=_require_non_empty(data.get("date"), "date"),
            price=ValueCoerce.as_float(data.get("price")),
            price_raw=ValueCoerce.as_float(data.get("price_raw")),
            price_hfq=ValueCoerce.as_float(data.get("price_hfq")),
            exit_ratio=ValueCoerce.as_float(data.get("exit_ratio"), default=1.0),
            profit=ValueCoerce.as_float(data.get("profit")),
            weighted_profit=ValueCoerce.as_float(data.get("weighted_profit")),
            reason=_require_non_empty(data.get("reason"), "reason"),
            roi=ValueCoerce.as_float(data.get("roi")),
        )


def _require_non_empty(value: Any, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} 不能为空")
    text = ValueCoerce.as_str(value)
    if not text:
        raise ValueError(f"{field_name} 不能为空")
    return text


__all__ = [
    "GoalAchievementRow",
]
