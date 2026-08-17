"""枚举 signal_snapshot sidecar 行模型（无 IO；读写见 ArtifactStore）。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Sequence

from core.modules.strategy.core.services.artifacts.layout import (
    SIGNAL_SNAPSHOTS_SUFFIX,
)
from core.modules.strategy.core.services.artifacts.tables.enum_investments import (
    _RowCoerce,
)

_JOIN_KEY = "investment_id"


@dataclass
class SignalSnapshotRow:
    """单笔命中的逻辑层 capture → sidecar 一行。"""

    investment_id: str
    values: Dict[str, Any] = field(default_factory=dict)

    def to_csv_row(self) -> Dict[str, Any]:
        row: Dict[str, Any] = {_JOIN_KEY: self.investment_id}
        row.update(self.values)
        return row

    @classmethod
    def from_csv_row(cls, raw: Dict[str, Any]) -> "SignalSnapshotRow":
        data = raw or {}
        investment_id = _RowCoerce.as_str(data.get(_JOIN_KEY))
        values = {
            str(key): value
            for key, value in data.items()
            if str(key) != _JOIN_KEY
        }
        return cls(investment_id=investment_id, values=values)


@dataclass
class EntitySignalSnapshotCsv:
    """单只股票的 capture 快照。

    列 = ``investment_id`` + capture key 并集；空 snapshot 不占行。
    """

    FILE_SUFFIX: ClassVar[str] = SIGNAL_SNAPSHOTS_SUFFIX
    JOIN_KEY: ClassVar[str] = _JOIN_KEY

    entity_id: str
    rows: List[SignalSnapshotRow] = field(default_factory=list)

    @classmethod
    def build(
        cls, entity_id: str, investments: Sequence[Dict[str, Any]]
    ) -> "EntitySignalSnapshotCsv":
        rows: List[SignalSnapshotRow] = []
        for investment in investments or []:
            if not isinstance(investment, dict):
                continue
            snapshot = investment.get("signal_snapshot")
            if not isinstance(snapshot, dict) or not snapshot:
                continue
            investment_id = _RowCoerce.require_investment_id(investment)
            values: Dict[str, Any] = {}
            for key, value in snapshot.items():
                name = str(key).strip()
                if not name or name == _JOIN_KEY:
                    continue
                values[name] = cls._cell(value)
            if values:
                rows.append(
                    SignalSnapshotRow(investment_id=investment_id, values=values)
                )
        return cls(entity_id=str(entity_id or "").strip(), rows=rows)

    @staticmethod
    def _cell(value: Any) -> Any:
        if value is None:
            return ""
        if isinstance(value, bool):
            return _RowCoerce.optional_bool_to_csv(value)
        if isinstance(value, (int, float, str)):
            return value
        return json.dumps(value, ensure_ascii=False, default=str)


__all__ = [
    "EntitySignalSnapshotCsv",
    "SignalSnapshotRow",
]
