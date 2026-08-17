"""枚举 version 归因 sidecar CSV（``{entity_id}_signal_snapshots.csv``）。

消费者: enumerator 写盘；分析读盘
边界: 按 investment_id 展开 ``signal_snapshot`` 标量列；不进成交表
不负责: P/O 交易回放（见 investment_csv）
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Sequence

from core.infra.utils import Utils
from core.modules.strategy.core.engines.shared.services.simulation_output.file_names import (
    SIGNAL_SNAPSHOTS_SUFFIX,
)
from core.modules.strategy.core.engines.shared.services.simulation_output.investment_csv import (
    _RowCoerce,
)
from core.modules.strategy.core.engines.shared.services.simulation_output.paths import (
    ArtifactPaths,
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
    """单只股票的 capture 快照 → ``{entity_id}_signal_snapshots.csv``。

    列 = ``investment_id`` + 本文件（含追加）capture key 并集；空 snapshot 不占行。
    """

    FILE_SUFFIX: ClassVar[str] = SIGNAL_SNAPSHOTS_SUFFIX

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

    @classmethod
    def load(cls, output_dir: Path, entity_id: str) -> "EntitySignalSnapshotCsv":
        path = cls.file_path(output_dir, entity_id)
        return cls(
            entity_id=str(entity_id or "").strip(),
            rows=[
                SignalSnapshotRow.from_csv_row(row)
                for row in Utils.io.read_csv_to_dicts(path)
                if _RowCoerce.as_str(row.get(_JOIN_KEY))
            ],
        )

    @classmethod
    def file_path(cls, output_dir: Path, entity_id: str) -> Path:
        return ArtifactPaths.signal_snapshots_path(output_dir, entity_id)

    @staticmethod
    def _cell(value: Any) -> Any:
        if value is None:
            return ""
        if isinstance(value, bool):
            return _RowCoerce.optional_bool_to_csv(value)
        if isinstance(value, (int, float, str)):
            return value
        return json.dumps(value, ensure_ascii=False, default=str)

    def save(self, output_dir: Path, *, append: bool = False) -> Path:
        path = self.file_path(output_dir, self.entity_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [row.to_csv_row() for row in self.rows]
        if append and path.is_file():
            rows = Utils.io.read_csv_to_dicts(path) + rows
        if not rows:
            return path
        keys: set[str] = set()
        for row in rows:
            keys.update(str(k) for k in row.keys())
        keys.discard(_JOIN_KEY)
        preferred = [_JOIN_KEY] + sorted(keys)
        Utils.io.write_dicts_to_csv(path, rows, preferred_order=preferred)
        return path


__all__ = [
    "EntitySignalSnapshotCsv",
    "SignalSnapshotRow",
]
