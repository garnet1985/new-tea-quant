"""BacktestEngine job dict contract shared by entity_based and slice_based modes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from core.modules.backtest_engine.core.shared.modes import BacktestMode

# 严谨契约：不允许 stock_id / symbol / ticker / entities 等别名
_ENTITY_BASED_ENTITY_KEY = "entity_specified"
_SLICE_BASED_ENTITY_KEY = "entity_ids"
_TIMELINE_POINT_COUNT_KEY = "timeline_point_count"


@dataclass(frozen=True)
class BacktestJob:
    """Job contract: ``{'id': str, 'payload': dict}``."""

    CONTRACT = "{'id': str, 'payload': dict}"
    ENTITY_BASED_ENTITY_KEY = _ENTITY_BASED_ENTITY_KEY
    SLICE_BASED_ENTITY_KEY = _SLICE_BASED_ENTITY_KEY
    TIMELINE_POINT_COUNT_KEY = _TIMELINE_POINT_COUNT_KEY

    id: str
    payload: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, job: Dict[str, Any]) -> BacktestJob:
        if not isinstance(job, dict):
            raise ValueError(f"BacktestEngine job 必须是 dict，契约 {cls.CONTRACT}")
        job_id = job.get("id")
        if job_id in (None, ""):
            raise ValueError(f"BacktestEngine job 必须使用契约 {cls.CONTRACT}")
        payload = job.get("payload")
        if not isinstance(payload, dict):
            raise ValueError(f"BacktestEngine job 必须使用契约 {cls.CONTRACT}")
        return cls(id=str(job_id), payload=dict(payload))

    @classmethod
    def validate_many(
        cls,
        jobs: List[Dict[str, Any]],
        *,
        mode: Optional[Union[str, Any]] = None,
    ) -> None:
        normalized_mode = cls._normalize_mode(mode) if mode is not None else None
        for index, job in enumerate(jobs):
            try:
                parsed = cls.from_dict(job)
                if normalized_mode is not None:
                    cls._validate_payload_for_mode(parsed.payload, normalized_mode)
            except ValueError as exc:
                raise ValueError(f"BacktestEngine job[{index}] invalid: {exc}") from exc

    @classmethod
    def _normalize_mode(cls, mode: Union[str, BacktestMode]) -> str:
        return BacktestMode.normalize(mode)

    @classmethod
    def _validate_payload_for_mode(cls, payload: Dict[str, Any], mode: str) -> None:
        if mode == BacktestMode.ENTITY_BASED.value:
            cls._validate_entity_based_payload(payload)
            return
        if mode == BacktestMode.SLICE_BASED.value:
            cls._validate_slice_based_payload(payload)
            return
        raise ValueError(f"unknown backtest mode: {mode!r}")

    @classmethod
    def _validate_entity_based_payload(cls, payload: Dict[str, Any]) -> None:
        entity_specified = payload.get(_ENTITY_BASED_ENTITY_KEY)
        if not isinstance(entity_specified, list):
            raise ValueError(
                f"entity_based payload requires {_ENTITY_BASED_ENTITY_KEY!r} (list)"
            )
        if not entity_specified:
            raise ValueError(f"entity_based payload {_ENTITY_BASED_ENTITY_KEY!r} 不能为空")
        for idx, item in enumerate(entity_specified):
            if not isinstance(item, dict) or "id" not in item:
                raise ValueError(
                    f"{_ENTITY_BASED_ENTITY_KEY}[{idx}] 必须是 dict 且包含 'id' 字段"
                )
            if not str(item.get("id") or "").strip():
                raise ValueError(f"{_ENTITY_BASED_ENTITY_KEY}[{idx}].id 不能为空")

    @classmethod
    def _validate_slice_based_payload(cls, payload: Dict[str, Any]) -> None:
        entity_ids = payload.get(_SLICE_BASED_ENTITY_KEY)
        if not isinstance(entity_ids, list) or not entity_ids:
            raise ValueError(
                f"slice_based payload requires non-empty {_SLICE_BASED_ENTITY_KEY!r}"
            )
        for idx, entity_id in enumerate(entity_ids):
            if not str(entity_id or "").strip():
                raise ValueError(f"{_SLICE_BASED_ENTITY_KEY}[{idx}] 不能为空")
        point_count = payload.get(_TIMELINE_POINT_COUNT_KEY)
        if not isinstance(point_count, int) or point_count <= 0:
            raise ValueError(
                f"slice_based payload requires positive int "
                f"{_TIMELINE_POINT_COUNT_KEY!r}（全量 points 不进 payload，由全局 calendar 解析）"
            )

    @classmethod
    def batch_payloads(cls, batch_entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not batch_entities:
            raise ValueError("BacktestEngine batch is empty")
        return [cls.from_dict(entity).payload for entity in batch_entities]

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "payload": dict(self.payload)}


__all__ = ["BacktestJob"]
