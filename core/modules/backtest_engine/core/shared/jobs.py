"""BacktestEngine job dict contract shared by entity_based and slice_based modes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from core.modules.backtest_engine.core.shared.modes import BacktestMode

_ENTITY_ID_KEYS = frozenset({"entity_id", "stock_id", "symbol", "ticker"})
_BULK_ENTITY_KEYS = frozenset({"entity_ids", "entities", "stock_ids"})
_ENTITY_BATCH_KEY = "jobs"


@dataclass(frozen=True)
class BacktestJob:
    """Job contract: ``{'id': str, 'payload': dict}``."""

    CONTRACT = "{'id': str, 'payload': dict}"

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
        batch = payload.get(_ENTITY_BATCH_KEY)
        if isinstance(batch, list):
            return
        if any(key in payload for key in _ENTITY_ID_KEYS):
            return
        raise ValueError(
            "entity_based payload requires entity_id/stock_id or jobs: List[job dict]"
        )

    @classmethod
    def _validate_slice_based_payload(cls, payload: Dict[str, Any]) -> None:
        if not cls._resolve_open_dates(payload):
            raise ValueError("slice_based payload requires open_dates")
        bulk_keys = _BULK_ENTITY_KEYS | _ENTITY_ID_KEYS
        if not any(key in payload for key in bulk_keys):
            raise ValueError(
                "slice_based payload requires entity_ids/stock_ids or equivalent bulk entity key"
            )

    @staticmethod
    def _resolve_open_dates(payload: Dict[str, Any]) -> List[str]:
        open_dates = payload.get("open_dates")
        if isinstance(open_dates, list) and open_dates:
            return [str(day) for day in open_dates if str(day).strip()]
        calendar = payload.get("calendar")
        if isinstance(calendar, dict):
            calendar_dates = calendar.get("open_dates")
            if isinstance(calendar_dates, list) and calendar_dates:
                return [str(day) for day in calendar_dates if str(day).strip()]
        return []

    @classmethod
    def batch_payloads(cls, batch_entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not batch_entities:
            raise ValueError("BacktestEngine batch is empty")
        return [cls.from_dict(entity).payload for entity in batch_entities]

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "payload": dict(self.payload)}


__all__ = ["BacktestJob"]
