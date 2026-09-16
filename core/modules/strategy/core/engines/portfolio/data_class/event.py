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
    # 相对买入股数的绝对份额；1.0 = 卖剩余全部。枚举分档 / 流动性拆段写入。
    exit_ratio: float = 1.0

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
            exit_ratio=_exit_ratio(raw.get("exit_ratio")),
        )

    @classmethod
    def from_enum_result(
        cls,
        row: "EnumResult",
        entity_id: str = "",
    ) -> List["PortfolioEvent"]:
        """一笔枚举结果 → buy/sell 事件。

        缺合法 ``entry_price_raw`` 时不生成任何事件。
        ``completed_goals`` 有成交切片则按切片生成多次卖（持仓归零才算完）。
        否则有卖出日即生成一笔 sell（不要求 ``exit_price_raw``）；资金层用 ``weighted_roi``。
        """
        eid = str(entity_id or getattr(row, "entity_id", "") or "").strip()
        iid = str(getattr(row, "investment_id", "") or "").strip()
        entry_date = str(getattr(row, "entry_date", "") or "").strip()
        entry_price_raw = float(getattr(row, "entry_price_raw", 0.0) or 0.0)
        entry_price_hfq = float(getattr(row, "entry_price_hfq", 0.0) or 0.0)
        if not entry_date or entry_price_raw <= 0:
            return []
        events: List["PortfolioEvent"] = [
            cls(
                kind="buy",
                date=entry_date,
                entity_id=eid,
                investment_id=iid,
                price=entry_price_raw,
                roi=0.0,
                entry_price_raw=entry_price_raw,
                entry_price_hfq=entry_price_hfq,
                bar_volume=_optional_float(getattr(row, "enter_bar_volume", None)),
            )
        ]
        slices = _exit_slices(row)
        if slices:
            for item in slices:
                events.append(
                    cls(
                        kind="sell",
                        date=item["date"],
                        entity_id=eid,
                        investment_id=iid,
                        price=float(item["price"] or 0.0),
                        roi=float(item["roi"] or 0.0),
                        entry_price_raw=entry_price_raw,
                        exit_price_raw=float(item["price"] or 0.0),
                        entry_price_hfq=entry_price_hfq,
                        exit_ratio=float(item["exit_ratio"]),
                    )
                )
            return events
        exit_date = str(getattr(row, "exit_date", "") or "").strip()
        if not exit_date:
            return events
        events.append(
            cls(
                kind="sell",
                date=exit_date,
                entity_id=eid,
                investment_id=iid,
                price=float(getattr(row, "exit_price_raw", 0.0) or 0.0),
                roi=float(getattr(row, "weighted_roi", 0.0) or 0.0),
                entry_price_raw=entry_price_raw,
                exit_price_raw=float(getattr(row, "exit_price_raw", 0.0) or 0.0),
                entry_price_hfq=entry_price_hfq,
                bar_volume=_optional_float(getattr(row, "exit_bar_volume", None)),
                exit_ratio=1.0,
            )
        )
        return events

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
        row = type("Row", (), {
            "entity_id": entity_id,
            "investment_id": investment_id,
            "entry_date": entry_date,
            "entry_price_raw": entry_price_raw,
            "entry_price_hfq": entry_price_hfq,
            "exit_date": exit_date,
            "exit_price_raw": exit_price_raw,
            "weighted_roi": weighted_roi,
            "enter_bar_volume": enter_bar_volume,
            "exit_bar_volume": exit_bar_volume,
            "completed_goals": (),
        })()
        return cls.from_enum_result(row, entity_id)


def _optional_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out > 0 else None


def _exit_ratio(value: Any) -> float:
    if value is None or value == "":
        return 1.0
    try:
        ratio = float(value)
    except (TypeError, ValueError):
        return 1.0
    if ratio <= 0:
        return 1.0
    return min(ratio, 1.0)


def _exit_slices(row: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for goal in getattr(row, "completed_goals", ()) or ():
        date = str(getattr(goal, "date", "") or "").strip()
        try:
            ratio = float(getattr(goal, "exit_ratio", 0.0) or 0.0)
        except (TypeError, ValueError):
            ratio = 0.0
        if not date or ratio <= 1e-12:
            continue
        try:
            roi = float(getattr(goal, "roi", 0.0) or 0.0)
        except (TypeError, ValueError):
            roi = 0.0
        try:
            price = float(getattr(goal, "price_raw", 0.0) or 0.0)
        except (TypeError, ValueError):
            price = 0.0
        out.append({"date": date, "exit_ratio": ratio, "roi": roi, "price": price})
    return out
