"""枚举结果管理器：按 entity 收 / 落 JSON / 还原 / 带范围查询。

边界:
- 负责: ``Investment`` → ``EnumResult`` 交还；``entities/{id}.json`` 读写；按 entity 筛选
- 不负责: tick 调度、价格锁仓、组合资金；不一次加载全市场
- 调用方: 枚举落盘；价格回测 worker；组合 build_events；枚举报告 / 分析 / BFF

查询必须带 ``entity_ids``。``filled`` = 有进场日；``completed`` = lifecycle complete。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from core.modules.strategy.core.engines.shared.enum_result_contract.enum_result import (
    EnumResult,
    results_from_document,
    results_to_document,
)
from core.modules.strategy.core.services.artifacts.consts import ENTITIES_SUBDIR
from core.modules.strategy.core.services.artifacts.io import ArtifactIO

_InvestmentLike = Any
_AcceptItem = Union[EnumResult, _InvestmentLike]


class EnumResultsManager:
    """一份 version 目录上的枚举结果袋（非单例；按进程 / 按目录建）。"""

    FILE_SUFFIX = ".json"
    DOCUMENT_KIND = "enum_results"

    def __init__(self, output_dir: Union[str, Path]) -> None:
        self.output_dir = Path(output_dir)
        self._by_entity: Dict[str, Tuple[EnumResult, ...]] = {}

    @classmethod
    def at(cls, output_dir: Union[str, Path]) -> "EnumResultsManager":
        return cls(output_dir)

    def entities_dir(self) -> Path:
        return self.output_dir / ENTITIES_SUBDIR

    def entity_path(self, entity_id: str) -> Path:
        eid = str(entity_id or "").strip()
        if not eid:
            raise ValueError("entity_id 不能为空")
        return self.entities_dir() / f"{eid}{self.FILE_SUFFIX}"

    def accept(self, entity_id: str, items: Sequence[_AcceptItem]) -> Tuple[EnumResult, ...]:
        """交还一只股票的全部结果（覆盖该 entity 内存袋，不自动写盘）。"""
        eid = str(entity_id or "").strip()
        if not eid:
            raise ValueError("entity_id 不能为空")
        results = tuple(self._coerce_item(item, eid) for item in items or ())
        self._by_entity[eid] = results
        return results

    def persist(self, entity_id: Optional[str] = None) -> List[Path]:
        """把内存袋写入 JSON。``entity_id`` 为空则写当前袋里所有 entity。"""
        if entity_id is not None:
            eid = str(entity_id or "").strip()
            if not eid:
                raise ValueError("entity_id 不能为空")
            path = self._write_entity(eid, self._by_entity.get(eid, ()))
            return [path] if path is not None else []
        written: List[Path] = []
        for eid, rows in self._by_entity.items():
            path = self._write_entity(eid, rows)
            if path is not None:
                written.append(path)
        return written

    def load(self, entity_ids: Sequence[str]) -> Dict[str, Tuple[EnumResult, ...]]:
        """按 id 从盘还原进内存（没有 JSON 则为空）。"""
        out: Dict[str, Tuple[EnumResult, ...]] = {}
        for raw_id in entity_ids or ():
            eid = str(raw_id or "").strip()
            if not eid:
                continue
            rows = self._read_entity(eid)
            self._by_entity[eid] = rows
            out[eid] = rows
        return out

    def for_entities(self, entity_ids: Sequence[str]) -> List[EnumResult]:
        """这些 entity 的全部结果（先 load）。"""
        rows: List[EnumResult] = []
        for eid, group in self.load(entity_ids).items():
            rows.extend(group)
        return rows

    def filled(self, entity_ids: Sequence[str]) -> List[EnumResult]:
        """这些 entity 里已成交进场的结果。"""
        return [row for row in self.for_entities(entity_ids) if row.is_filled()]

    def completed(self, entity_ids: Sequence[str]) -> List[EnumResult]:
        """这些 entity 里 lifecycle=complete 的结果（含未买成的 abort）。"""
        return [row for row in self.for_entities(entity_ids) if row.is_complete()]

    def results(self, entity_id: str) -> Tuple[EnumResult, ...]:
        eid = str(entity_id or "").strip()
        if not eid:
            return ()
        if eid not in self._by_entity:
            self.load([eid])
        return self._by_entity.get(eid, ())

    def list_entities(self) -> List[str]:
        """磁盘上已有 JSON 的 entity（加内存袋里尚未落盘的）。不读文件内容。"""
        found = set(self._by_entity.keys())
        directory = self.entities_dir()
        if directory.is_dir():
            suffix = self.FILE_SUFFIX
            for entry in directory.iterdir():
                if entry.is_file() and entry.name.endswith(suffix):
                    found.add(entry.name[: -len(suffix)])
        return sorted(found)

    def _coerce_item(self, item: _AcceptItem, entity_id: str) -> EnumResult:
        if isinstance(item, EnumResult):
            return item.with_entity_id(entity_id)
        return EnumResult.from_investment(item, entity_id=entity_id)

    def _write_entity(
        self, entity_id: str, rows: Sequence[EnumResult]
    ) -> Optional[Path]:
        if not rows:
            return None
        path = self.entity_path(entity_id)
        ArtifactIO.write_json(path, results_to_document(entity_id, rows))
        return path

    def _read_entity(self, entity_id: str) -> Tuple[EnumResult, ...]:
        path = self.entity_path(entity_id)
        if not path.is_file():
            return ()
        payload = ArtifactIO.read_json(path)
        _eid, rows = results_from_document(payload, entity_id=entity_id)
        return tuple(rows)


__all__ = ["EnumResultsManager"]
