"""Opportunity — 扫描/枚举信号记录（scan → Investment / adapter）。

消费者: scanner, enumerator, portfolio
其它: contracts, hooks

本文件:
- StockInfo / OpportunityMeta / OpportunityContributor / Opportunity
  边界: 负责入场条件快照（trigger_*）；不含 exit、lifecycle、goal 完成字段（见 Investment）
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional, Tuple


@dataclass
class StockInfo:
    id: str = ""
    name: str = ""
    industry: str = ""
    type: str = ""
    exchange_center: str = ""
    delist_date: str = ""

    @classmethod
    def from_dict(cls, raw: Any) -> "StockInfo":
        data = raw if isinstance(raw, dict) else {}
        return cls(
            id=str(data.get("id") or ""),
            name=str(data.get("name") or ""),
            industry=str(data.get("industry") or ""),
            type=str(data.get("type") or ""),
            exchange_center=str(data.get("exchange_center") or ""),
            delist_date=str(data.get("delist_date") or data.get("delisted_date") or ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OpportunityMeta:
    opportunity_id: str = ""
    scan_date: str = ""
    created_at: str = ""
    updated_at: str = ""
    config_hash: str = ""


@dataclass
class OpportunityContributor:
    strategy_name: str = ""
    strategy_version: str = ""


@dataclass
class Opportunity:
    """Records a strategy scan signal; trading state lives on ``Investment``.

    Signal fields use ``trigger_*``; post-fill trade fields use ``entry_*`` / ``exit_info.*``.
    """

    STATUS_AT_TRIGGER_KEY: ClassVar[str] = "stock_status_at_trigger"

    stock: StockInfo
    record_of_today: Dict[str, Any]
    trigger_date: str = ""
    trigger_price: float = 0.0
    trigger_price_raw: float = 0.0
    market_profile: str = ""
    meta: OpportunityMeta = field(default_factory=OpportunityMeta)
    contributor: OpportunityContributor = field(default_factory=OpportunityContributor)
    extra_fields: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def stock_id(self) -> str:
        if isinstance(self.stock, StockInfo):
            return str(self.stock.id or "").strip()
        if isinstance(self.stock, dict):
            return str(self.stock.get("id") or "").strip()
        return ""

    @property
    def stock_name(self) -> str:
        if isinstance(self.stock, StockInfo):
            return str(self.stock.name or self.stock.id or "").strip()
        if isinstance(self.stock, dict):
            return str(
                self.stock.get("name") or self.stock.get("id") or ""
            ).strip()
        return ""

    def __post_init__(self) -> None:
        if isinstance(self.stock, dict):
            self.stock = StockInfo.from_dict(self.stock)
        if not self.trigger_date and self.record_of_today:
            self.trigger_date = str(self.record_of_today.get("date") or "")
        if not self.trigger_price and self.record_of_today:
            self.trigger_price = float(self.record_of_today.get("close") or 0.0)
        if not self.trigger_price_raw and self.record_of_today:
            raw = self.record_of_today.get("raw")
            if isinstance(raw, dict):
                self.trigger_price_raw = float(raw.get("close") or 0.0)
        if not self.meta.created_at:
            self.meta.created_at = datetime.now().isoformat()
        if not self.meta.updated_at:
            self.meta.updated_at = datetime.now().isoformat()

    def add_contributor(
        self,
        strategy_name: str,
        strategy_version: str = "1.0",
        opportunity_id: Optional[str] = None,
    ) -> None:
        self.contributor.strategy_name = strategy_name
        self.contributor.strategy_version = strategy_version
        self.meta.scan_date = datetime.now().strftime("%Y%m%d")
        if not self.meta.opportunity_id and opportunity_id:
            self.meta.opportunity_id = opportunity_id
        if not self.trigger_date and self.record_of_today:
            self.trigger_date = str(self.record_of_today.get("date") or "")
        if not self.trigger_price and self.record_of_today:
            self.trigger_price = float(self.record_of_today.get("close") or 0.0)
        if not self.trigger_price_raw and self.record_of_today:
            raw = self.record_of_today.get("raw")
            if isinstance(raw, dict):
                self.trigger_price_raw = float(raw.get("close") or 0.0)
        self.meta.updated_at = datetime.now().isoformat()

    def bind_scan_context(
        self,
        *,
        strategy_name: str,
        stock_id: str,
        stock_info: Optional[Dict[str, Any]] = None,
        trigger_date: Optional[str] = None,
        trigger_price: Optional[float] = None,
        trigger_price_raw: Optional[float] = None,
        opportunity_index: Optional[int] = None,
        market_profile: Optional[str] = None,
    ) -> "Opportunity":
        """补全枚举/scan 运行时上下文（策略 hook 只产出信号，引擎填入 meta/stock/trigger）。"""
        if trigger_price is not None:
            # qfq 信号价可为负/0（前复权穿越零轴）；裸价成交层才要求 > 0
            self.trigger_price = float(trigger_price)
        if trigger_price_raw is not None:
            self.trigger_price_raw = float(trigger_price_raw)
        if trigger_date is not None:
            self.trigger_date = str(trigger_date)
            self.meta.scan_date = str(trigger_date)
        if opportunity_index is not None:
            self.meta.opportunity_id = str(opportunity_index)
        if market_profile is not None:
            self.market_profile = str(market_profile).strip()
        self.contributor.strategy_name = strategy_name

        merged = dict(stock_info or {})
        merged = {**self.stock.to_dict(), **merged}
        merged.setdefault("id", stock_id)
        self.stock = StockInfo.from_dict(merged)
        self.meta.updated_at = datetime.now().isoformat()
        return self

    def stamp_status_at_trigger(
        self,
        *,
        status_tags_provider: Any,
        trade_date: Optional[str] = None,
    ) -> Tuple[str, ...]:
        """写入 ``metadata.stock_status_at_trigger``（触发日 ST 等标签）。

        - 有 provider：写入标签列表（无状态则为 ``[]``）
        - 无 provider：不改 metadata，返回空 tuple
        """
        if status_tags_provider is None:
            return ()
        day = str(
            trade_date if trade_date is not None else self.trigger_date or ""
        ).strip()
        entity_id = ""
        if isinstance(self.stock, StockInfo):
            entity_id = str(self.stock.id or "").strip()
        elif isinstance(self.stock, dict):
            entity_id = str(self.stock.get("id") or "").strip()
        tags: List[str] = []
        if day and entity_id:
            raw = status_tags_provider.status_tags_at(entity_id, day)
            if raw:
                tags = [str(t).strip() for t in raw if str(t).strip()]
        if not isinstance(self.metadata, dict):
            self.metadata = {}
        self.metadata[self.STATUS_AT_TRIGGER_KEY] = tags
        self.meta.updated_at = datetime.now().isoformat()
        return tuple(tags)

    def status_tags_at_trigger(self) -> Tuple[str, ...]:
        """读取已打标的触发日状态；未打标返回空。"""
        raw = self.metadata.get(self.STATUS_AT_TRIGGER_KEY) if isinstance(self.metadata, dict) else None
        if not isinstance(raw, (list, tuple)):
            return ()
        return tuple(str(t).strip() for t in raw if str(t).strip())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Opportunity":
        raw = dict(data or {})
        stock = StockInfo.from_dict(raw.get("stock"))
        meta_raw = raw.get("meta") if isinstance(raw.get("meta"), dict) else {}
        contributor_raw = raw.get("contributor") if isinstance(raw.get("contributor"), dict) else {}
        meta = OpportunityMeta(**{f.name: meta_raw.get(f.name, "") for f in fields(OpportunityMeta)})
        contributor = OpportunityContributor(
            **{f.name: contributor_raw.get(f.name, "") for f in fields(OpportunityContributor)}
        )
        trigger_price = cls._to_float(raw.get("trigger_price"), 0.0)
        trigger_price_raw = cls._to_float(raw.get("trigger_price_raw"), 0.0)
        return cls(
            stock=stock,
            record_of_today=dict(raw.get("record_of_today") or {}),
            trigger_date=str(raw.get("trigger_date") or ""),
            trigger_price=trigger_price,
            trigger_price_raw=trigger_price_raw,
            market_profile=str(raw.get("market_profile") or ""),
            meta=meta,
            contributor=contributor,
            extra_fields=dict(raw.get("extra_fields") or {}),
            metadata=dict(raw.get("metadata") or {}),
        )

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        if value is None or value == "":
            return default
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value).strip())
        except (TypeError, ValueError):
            return default


__all__ = [
    "Opportunity",
    "OpportunityContributor",
    "OpportunityMeta",
    "StockInfo",
]
