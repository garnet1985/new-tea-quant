"""Portfolio 买卖事件（由 enum InvestmentRow 展开）。

本文件:
- PortfolioEvent: buy/sell 事件；定价规则见类 docstring
  边界: 负责事件模型与 from_investment_row；不负责 simulate 或 hooks
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.enumerator.shared.report_manager.stock_investments import (
        InvestmentRow,
    )


@dataclass
class PortfolioEvent:
    """资金回放事件（替换 legacy trigger/target）。

    - buy: ``price`` = ``entry_price_raw``（来自 enter_price 对应 raw 字段，
      默认 next_open→raw open；**不用** raw close 定仓）
    - sell: ``price`` = ``entry_price_raw * (1 + roi)``（**不用** exit_price_raw / raw close）
      其中 roi 来自枚举 ``weighted_roi``（前复权收益率）
    """

    kind: str
    date: str
    entity_id: str
    investment_id: str
    price: float
    # roi: return on investment（来自枚举 weighted_roi）；buy 事件为 0
    roi: float = 0.0
    entry_price_raw: float = 0.0
    exit_price_raw: float = 0.0
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
            bar_volume=_optional_float(raw.get("bar_volume")),
        )

    @classmethod
    def from_investment_row(
        cls,
        row: "InvestmentRow",
        entity_id: str,
    ) -> List["PortfolioEvent"]:
        """一笔枚举 investment → buy/sell 事件。

        缺 ``entry_price_raw`` 时不生成任何事件（避免用前复权价定仓）。
        """
        eid = str(entity_id or "").strip()
        inv_id = str(getattr(row, "investment_id", "") or "").strip()
        entry_date = str(getattr(row, "entry_date", "") or "").strip()
        entry_raw = float(getattr(row, "entry_price_raw", 0.0) or 0.0)
        exit_date = str(getattr(row, "exit_date", "") or "").strip()
        exit_raw = float(getattr(row, "exit_price_raw", 0.0) or 0.0)
        # weighted_roi: 枚举层用前复权价算的加权 roi
        roi = float(getattr(row, "weighted_roi", 0.0) or 0.0)

        if not entry_date or entry_raw <= 0:
            return []

        events: List[PortfolioEvent] = [
            cls(
                kind="buy",
                date=entry_date,
                entity_id=eid,
                investment_id=inv_id,
                price=entry_raw,
                roi=0.0,
                entry_price_raw=entry_raw,
                exit_price_raw=exit_raw,
                bar_volume=_optional_float(getattr(row, "buy_bar_volume", None)),
            )
        ]
        if exit_date and entry_raw > 0:
            sell_price = entry_raw * (1.0 + roi)
            events.append(
                cls(
                    kind="sell",
                    date=exit_date,
                    entity_id=eid,
                    investment_id=inv_id,
                    price=sell_price,
                    roi=roi,
                    entry_price_raw=entry_raw,
                    exit_price_raw=exit_raw,
                    bar_volume=_optional_float(getattr(row, "sell_bar_volume", None)),
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
