"""Opportunity — scan signal record (shared across scan / enumerate / simulate).

Terminology (with ``Investment``):
- ``trigger_date`` / ``trigger_price``: signal bar on the scan record.
- ``entry_*`` / ``exit_info.*`` / ``direction``: filled trade state on ``Investment``.
- ``completed_goals``: each partial or full exit leg produced by goal checks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class StockInfo:
    id: str = ""
    name: str = ""
    industry: str = ""
    type: str = ""
    exchange_center: str = ""

    @classmethod
    def from_dict(cls, raw: Any) -> "StockInfo":
        data = raw if isinstance(raw, dict) else {}
        return cls(
            id=str(data.get("id") or ""),
            name=str(data.get("name") or ""),
            industry=str(data.get("industry") or ""),
            type=str(data.get("type") or ""),
            exchange_center=str(data.get("exchange_center") or ""),
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

    stock: StockInfo
    record_of_today: Dict[str, Any]
    trigger_date: str = ""
    trigger_price: float = 0.0
    meta: OpportunityMeta = field(default_factory=OpportunityMeta)
    contributor: OpportunityContributor = field(default_factory=OpportunityContributor)
    extra_fields: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.stock, dict):
            self.stock = StockInfo.from_dict(self.stock)
        if not self.trigger_date and self.record_of_today:
            self.trigger_date = str(self.record_of_today.get("date") or "")
        if not self.trigger_price and self.record_of_today:
            self.trigger_price = float(self.record_of_today.get("close") or 0.0)
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
        self.meta.updated_at = datetime.now().isoformat()

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
        return cls(
            stock=stock,
            record_of_today=dict(raw.get("record_of_today") or {}),
            trigger_date=str(raw.get("trigger_date") or ""),
            trigger_price=trigger_price,
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
