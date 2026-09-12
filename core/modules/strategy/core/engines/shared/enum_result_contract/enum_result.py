"""跨回测层的枚举结果对象（冻结投影；不含 tick）。

边界:
- 负责: 从 ``Investment`` 投影；JSON 往返；选仓用的 ``Opportunity`` 投影
- 不负责: 生命周期模拟、文件 IO（见 EnumResultsManager）
- 调用方: EnumResultsManager；价格回测 worker；组合选仓 / 事件展开

字段口径与现有枚举 CSV 一致：价无后缀 = qfq；``*_raw`` 成交；``*_hfq`` 比例 / ROI。
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

from core.modules.strategy.core.helpers.coerce import ValueCoerce

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.shared.data_class.investment.investment import (
        Investment,
    )
    from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity


@dataclass(frozen=True)
class CompletedGoal:
    """一笔已成交目标（分档卖 / 到期 / 保护 / 动态等）。"""

    name: str = ""
    date: str = ""
    price: float = 0.0
    price_raw: float = 0.0
    price_hfq: float = 0.0
    exit_ratio: float = 0.0
    profit: float = 0.0
    weighted_profit: float = 0.0
    reason: str = ""
    roi: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
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
    def from_dict(cls, raw: Any) -> "CompletedGoal":
        data = raw if isinstance(raw, dict) else {}
        name = ValueCoerce.as_str(data.get("name") or data.get("goal_name"))
        return cls(
            name=name,
            date=ValueCoerce.as_str(data.get("date")),
            price=ValueCoerce.as_float(data.get("price")),
            price_raw=ValueCoerce.as_float(data.get("price_raw")),
            price_hfq=ValueCoerce.as_float(data.get("price_hfq")),
            exit_ratio=ValueCoerce.as_float(data.get("exit_ratio"), default=1.0),
            profit=ValueCoerce.as_float(data.get("profit")),
            weighted_profit=ValueCoerce.as_float(data.get("weighted_profit")),
            reason=ValueCoerce.as_str(data.get("reason")),
            roi=ValueCoerce.as_float(data.get("roi")),
        )


@dataclass(frozen=True)
class EnumResult:
    """一笔枚举机会的冻结结果。不可 ``try_enter`` / ``check_targets``。"""

    entity_id: str = ""
    investment_id: str = ""
    trigger_date: str = ""
    trigger_price: float = 0.0
    trigger_price_raw: float = 0.0
    trigger_price_hfq: float = 0.0
    entry_date: str = ""
    entry_price: float = 0.0
    entry_price_raw: float = 0.0
    entry_price_hfq: float = 0.0
    exit_date: str = ""
    exit_price: float = 0.0
    exit_price_raw: float = 0.0
    exit_price_hfq: float = 0.0
    exit_reason: str = ""
    lifecycle: str = ""
    result: str = ""
    weighted_roi: float = 0.0
    holding_days: int = 0
    enter_prev_close: Optional[float] = None
    enter_at_limit: Optional[bool] = None
    exit_prev_close: Optional[float] = None
    exit_at_limit: Optional[bool] = None
    stock_status_at_trigger: Tuple[str, ...] = ()
    enter_bar_volume: Optional[float] = None
    exit_bar_volume: Optional[float] = None
    completed_goals: Tuple[CompletedGoal, ...] = ()
    signal_snapshot: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "stock_status_at_trigger", tuple(self.stock_status_at_trigger or ())
        )
        object.__setattr__(
            self,
            "completed_goals",
            tuple(
                item
                if isinstance(item, CompletedGoal)
                else CompletedGoal.from_dict(item)
                for item in (self.completed_goals or ())
            ),
        )
        object.__setattr__(self, "signal_snapshot", dict(self.signal_snapshot or {}))

    def is_filled(self) -> bool:
        """已成交进场（价格层消费口径）。"""
        return bool(str(self.entry_date or "").strip())

    def is_complete(self) -> bool:
        return str(self.lifecycle or "").strip().lower() == "complete"

    def with_entity_id(self, entity_id: str) -> "EnumResult":
        eid = str(entity_id or "").strip()
        if eid == self.entity_id:
            return self
        return replace(self, entity_id=eid)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "investment_id": self.investment_id,
            "trigger_date": self.trigger_date,
            "trigger_price": self.trigger_price,
            "trigger_price_raw": self.trigger_price_raw,
            "trigger_price_hfq": self.trigger_price_hfq,
            "entry_date": self.entry_date,
            "entry_price": self.entry_price,
            "entry_price_raw": self.entry_price_raw,
            "entry_price_hfq": self.entry_price_hfq,
            "exit_date": self.exit_date,
            "exit_price": self.exit_price,
            "exit_price_raw": self.exit_price_raw,
            "exit_price_hfq": self.exit_price_hfq,
            "exit_reason": self.exit_reason,
            "lifecycle": self.lifecycle,
            "result": self.result,
            "weighted_roi": self.weighted_roi,
            "holding_days": self.holding_days,
            "enter_prev_close": self.enter_prev_close,
            "enter_at_limit": self.enter_at_limit,
            "exit_prev_close": self.exit_prev_close,
            "exit_at_limit": self.exit_at_limit,
            "stock_status_at_trigger": list(self.stock_status_at_trigger),
            "enter_bar_volume": self.enter_bar_volume,
            "exit_bar_volume": self.exit_bar_volume,
            "completed_goals": [goal.to_dict() for goal in self.completed_goals],
            "signal_snapshot": dict(self.signal_snapshot),
        }

    @classmethod
    def from_dict(cls, raw: Any, *, entity_id: str = "") -> "EnumResult":
        data = raw if isinstance(raw, dict) else {}
        eid = str(entity_id or "").strip() or ValueCoerce.as_str(data.get("entity_id"))
        return cls(
            entity_id=eid,
            investment_id=ValueCoerce.as_str(
                data.get("investment_id") or data.get("opportunity_id")
            ),
            trigger_date=ValueCoerce.as_str(data.get("trigger_date")),
            trigger_price=ValueCoerce.as_float(data.get("trigger_price")),
            trigger_price_raw=ValueCoerce.as_float(data.get("trigger_price_raw")),
            trigger_price_hfq=ValueCoerce.as_float(data.get("trigger_price_hfq")),
            entry_date=ValueCoerce.as_str(data.get("entry_date")),
            entry_price=ValueCoerce.as_float(data.get("entry_price")),
            entry_price_raw=ValueCoerce.as_float(data.get("entry_price_raw")),
            entry_price_hfq=ValueCoerce.as_float(data.get("entry_price_hfq")),
            exit_date=ValueCoerce.as_str(data.get("exit_date")),
            exit_price=ValueCoerce.as_float(data.get("exit_price")),
            exit_price_raw=ValueCoerce.as_float(data.get("exit_price_raw")),
            exit_price_hfq=ValueCoerce.as_float(data.get("exit_price_hfq")),
            exit_reason=ValueCoerce.as_str(data.get("exit_reason")),
            lifecycle=ValueCoerce.as_str(data.get("lifecycle")),
            result=ValueCoerce.as_str(data.get("result")),
            weighted_roi=ValueCoerce.as_float(data.get("weighted_roi")),
            holding_days=ValueCoerce.as_int(data.get("holding_days")),
            enter_prev_close=ValueCoerce.as_optional_float(data.get("enter_prev_close")),
            enter_at_limit=ValueCoerce.as_optional_bool(data.get("enter_at_limit")),
            exit_prev_close=ValueCoerce.as_optional_float(data.get("exit_prev_close")),
            exit_at_limit=ValueCoerce.as_optional_bool(data.get("exit_at_limit")),
            stock_status_at_trigger=ValueCoerce.as_str_tuple(
                data.get("stock_status_at_trigger")
            ),
            enter_bar_volume=ValueCoerce.as_optional_float(data.get("enter_bar_volume")),
            exit_bar_volume=ValueCoerce.as_optional_float(data.get("exit_bar_volume")),
            completed_goals=tuple(
                CompletedGoal.from_dict(item)
                for item in (data.get("completed_goals") or [])
                if isinstance(item, dict)
            ),
            signal_snapshot=dict(data.get("signal_snapshot") or {}),
        )

    @classmethod
    def from_investment(
        cls,
        investment: "Investment",
        *,
        entity_id: str = "",
    ) -> "EnumResult":
        """从枚举器 ``Investment`` 投影；丢掉 settings / pending / last_bar 等运行时态。"""
        eid = str(entity_id or "").strip() or ValueCoerce.as_str(
            getattr(investment, "stock_id", "")
        )
        meta = getattr(investment, "meta", None)
        investment_id = ValueCoerce.as_str(
            getattr(meta, "opportunity_id", "") if meta is not None else ""
        )
        entry = getattr(investment, "entry", None)
        exit_info = getattr(investment, "exit_info", None)
        holding = getattr(investment, "holding", None)
        outcome = getattr(investment, "outcome", None)
        tags = ()
        stamp = getattr(investment, "status_tags_at_trigger", None)
        if callable(stamp):
            tags = tuple(stamp() or ())
        goals_raw = getattr(investment, "completed_goals", None) or []
        snapshot = getattr(investment, "signal_snapshot", None)
        return cls(
            entity_id=eid,
            investment_id=investment_id,
            trigger_date=ValueCoerce.as_str(getattr(investment, "trigger_date", "")),
            trigger_price=ValueCoerce.as_float(getattr(investment, "trigger_price", 0.0)),
            trigger_price_raw=ValueCoerce.as_float(
                getattr(investment, "trigger_price_raw", 0.0)
            ),
            trigger_price_hfq=ValueCoerce.as_float(
                getattr(investment, "trigger_price_hfq", 0.0)
            ),
            entry_date=ValueCoerce.as_str(
                getattr(entry, "date", "") if entry is not None else ""
            ),
            entry_price=ValueCoerce.as_float(
                getattr(entry, "price", 0.0) if entry is not None else 0.0
            ),
            entry_price_raw=ValueCoerce.as_float(
                getattr(entry, "price_raw", 0.0) if entry is not None else 0.0
            ),
            entry_price_hfq=ValueCoerce.as_float(
                getattr(entry, "price_hfq", 0.0) if entry is not None else 0.0
            ),
            exit_date=ValueCoerce.as_str(
                getattr(exit_info, "date", "") if exit_info is not None else ""
            ),
            exit_price=ValueCoerce.as_float(
                getattr(exit_info, "price", 0.0) if exit_info is not None else 0.0
            ),
            exit_price_raw=ValueCoerce.as_float(
                getattr(exit_info, "price_raw", 0.0) if exit_info is not None else 0.0
            ),
            exit_price_hfq=ValueCoerce.as_float(
                getattr(exit_info, "price_hfq", 0.0) if exit_info is not None else 0.0
            ),
            exit_reason=ValueCoerce.as_str(
                getattr(exit_info, "reason", "") if exit_info is not None else ""
            ),
            lifecycle=ValueCoerce.as_str(getattr(investment, "lifecycle", "")),
            result=ValueCoerce.as_str(
                getattr(outcome, "result", "") if outcome is not None else ""
            ),
            weighted_roi=ValueCoerce.as_float(
                getattr(outcome, "weighted_roi", 0.0) if outcome is not None else 0.0
            ),
            holding_days=ValueCoerce.as_int(
                getattr(holding, "days", 0) if holding is not None else 0
            ),
            enter_prev_close=(
                ValueCoerce.as_optional_float(getattr(entry, "prev_close", None))
                if entry is not None
                else None
            ),
            enter_at_limit=(
                ValueCoerce.as_optional_bool(getattr(entry, "at_limit", None))
                if entry is not None
                else None
            ),
            exit_prev_close=(
                ValueCoerce.as_optional_float(getattr(exit_info, "prev_close", None))
                if exit_info is not None
                else None
            ),
            exit_at_limit=(
                ValueCoerce.as_optional_bool(getattr(exit_info, "at_limit", None))
                if exit_info is not None
                else None
            ),
            stock_status_at_trigger=tags,
            enter_bar_volume=(
                ValueCoerce.as_optional_float(getattr(entry, "bar_volume", None))
                if entry is not None
                else None
            ),
            exit_bar_volume=(
                ValueCoerce.as_optional_float(getattr(exit_info, "bar_volume", None))
                if exit_info is not None
                else None
            ),
            completed_goals=tuple(
                CompletedGoal.from_dict(item)
                for item in goals_raw
                if isinstance(item, dict)
            ),
            signal_snapshot=dict(snapshot or {}) if isinstance(snapshot, dict) else {},
        )

    def to_opportunity(self) -> "Opportunity":
        """选仓投影：只留信号字段，屏蔽 entry / exit / result / roi。"""
        from core.modules.strategy.core.engines.shared.data_class.opportunity import (
            Opportunity,
            OpportunityMeta,
            StockInfo,
        )

        metadata: Dict[str, Any] = {}
        if self.stock_status_at_trigger:
            metadata[Opportunity.STATUS_AT_TRIGGER_KEY] = list(
                self.stock_status_at_trigger
            )
        return Opportunity(
            stock=StockInfo(id=self.entity_id),
            record_of_today={},
            trigger_date=self.trigger_date,
            trigger_price=float(self.trigger_price or 0.0),
            trigger_price_raw=float(self.trigger_price_raw or 0.0),
            trigger_price_hfq=float(self.trigger_price_hfq or 0.0),
            meta=OpportunityMeta(
                opportunity_id=self.investment_id,
                scan_date=self.trigger_date,
            ),
            metadata=metadata,
        )


def results_to_document(
    entity_id: str, results: Sequence[EnumResult]
) -> Dict[str, Any]:
    eid = str(entity_id or "").strip()
    return {
        "kind": "enum_results",
        "entity_id": eid,
        "results": [item.with_entity_id(eid).to_dict() for item in results],
    }


def results_from_document(
    payload: Any, *, entity_id: str = ""
) -> Tuple[str, List[EnumResult]]:
    data = payload if isinstance(payload, dict) else {}
    eid = str(entity_id or "").strip() or ValueCoerce.as_str(data.get("entity_id"))
    rows = data.get("results")
    if not isinstance(rows, list):
        return eid, []
    return eid, [EnumResult.from_dict(item, entity_id=eid) for item in rows]


__all__ = [
    "CompletedGoal",
    "EnumResult",
    "results_from_document",
    "results_to_document",
]
