"""Portfolio 买卖事件（由 EnumResult 展开）。

本文件:
- PortfolioEvent: buy/sell 事件；定价规则见类 docstring
  边界: 负责事件模型与 from_enum_result；不负责 simulate 或 hooks
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class PortfolioEvent:
    """资金回放事件（替换 legacy trigger/target）。

    买入扣现金用 ``entry_price_raw``。平仓盈利用枚举 hfq ``weighted_roi``：
    ``股数 × 买入 raw × ROI``。``exit_price_raw`` 仅审计，不参与资金。
    买入 ``entry_price_hfq`` 给日频盯市当 ROI 分母。

    - buy: ``price`` = ``entry_price_raw``
    - sell: ``price`` = ``exit_price_raw``（可缺；模拟器用 ``roi`` 算钱）
    """

    kind: str
    date: str
    entity_id: str
    investment_id: str
    price: float
    # roi: return on investment（来自枚举 weighted_roi / hfq）；buy 事件为 0
    roi: float = 0.0
    entry_price_raw: float = 0.0
    exit_price_raw: float = 0.0
    # 买入成交后复权价；日频盯市 ROI 分母（不是买入日收盘）
    entry_price_hfq: float = 0.0
    # 成交日 bar 成交量（股）；buy / sell 事件各自带当日 volume
    bar_volume: Optional[float] = None

    def is_buy(self) -> bool:
        return str(self.kind or "").strip().lower() == "buy"

    def is_sell(self) -> bool:
        return str(self.kind or "").strip().lower() == "sell"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PortfolioEvent":
        raw = data or {}
        return cls(
            kind=str(raw.get("kind") or "").strip().lower(),
            date=str(raw.get("date") or "").strip(),
            entity_id=str(raw.get("entity_id") or "").strip(),
            investment_id=str(raw.get("investment_id") or "").strip(),
            price=float(raw.get("price") or 0.0),
            roi=float(raw.get("roi") or 0.0),
            entry_price_raw=float(raw.get("entry_price_raw") or 0.0),
            exit_price_raw=float(raw.get("exit_price_raw") or 0.0),
            entry_price_hfq=float(raw.get("entry_price_hfq") or 0.0),
            bar_volume=_optional_float(raw.get("bar_volume")),
        )

    @classmethod
    def from_enum_result(
        cls,
        row: "EnumResult",
        entity_id: str = "",
    ) -> List["PortfolioEvent"]:
        """一笔枚举结果 → buy/sell 事件。

        缺合法 ``entry_price_raw`` 时不生成任何事件。
        有卖出日即生成 sell（不要求 ``exit_price_raw``）；资金层用 ``weighted_roi``。
        """
        eid = str(entity_id or getattr(row, "entity_id", "") or "").strip()
        return cls._from_fill(
            entity_id=eid,
            investment_id=str(getattr(row, "investment_id", "") or "").strip(),
            entry_date=str(getattr(row, "entry_date", "") or "").strip(),
            entry_price_raw=float(getattr(row, "entry_price_raw", 0.0) or 0.0),
            entry_price_hfq=float(getattr(row, "entry_price_hfq", 0.0) or 0.0),
            exit_date=str(getattr(row, "exit_date", "") or "").strip(),
            exit_price_raw=float(getattr(row, "exit_price_raw", 0.0) or 0.0),
            weighted_roi=float(getattr(row, "weighted_roi", 0.0) or 0.0),
            enter_bar_volume=getattr(row, "enter_bar_volume", None),
            exit_bar_volume=getattr(row, "exit_bar_volume", None),
        )

    @classmethod
    def _from_fill(
        cls,
        *,
        entity_id: str,
        investment_id: str,
        entry_date: str,
        entry_price_raw: float,
        entry_price_hfq: float,
        exit_date: str,
        exit_price_raw: float,
        weighted_roi: float,
        enter_bar_volume: Any,
        exit_bar_volume: Any,
    ) -> List["PortfolioEvent"]:
        if not entry_date or entry_price_raw <= 0:
            return []
        events: List[PortfolioEvent] = [
            cls(
                kind="buy",
                date=entry_date,
                entity_id=entity_id,
                investment_id=investment_id,
                price=entry_price_raw,
                roi=0.0,
                entry_price_raw=entry_price_raw,
                exit_price_raw=exit_price_raw,
                entry_price_hfq=float(entry_price_hfq or 0.0),
                bar_volume=_optional_float(enter_bar_volume),
            )
        ]
        if exit_date:
            events.append(
                cls(
                    kind="sell",
                    date=exit_date,
                    entity_id=entity_id,
                    investment_id=investment_id,
                    price=exit_price_raw,
                    roi=weighted_roi,
                    entry_price_raw=entry_price_raw,
                    exit_price_raw=exit_price_raw,
                    entry_price_hfq=float(entry_price_hfq or 0.0),
                    bar_volume=_optional_float(exit_bar_volume),
                )
            )
        return events


def _optional_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out > 0 else None
