"""BacktestEngine job wire format shared by timeline and sliced modes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class BacktestJob:
    """Wire-format job: ``{'id': str, 'payload': dict}``."""

    CONTRACT = "{'id': str, 'payload': dict}"

    id: str
    payload: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_wire(cls, job: Dict[str, Any]) -> BacktestJob:
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
    def validate_many(cls, jobs: List[Dict[str, Any]]) -> None:
        for index, job in enumerate(jobs):
            try:
                cls.from_wire(job)
            except ValueError as exc:
                raise ValueError(f"BacktestEngine job[{index}] invalid: {exc}") from exc

    @classmethod
    def batch_payloads(cls, batch_entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not batch_entities:
            raise ValueError("BacktestEngine batch is empty")
        return [cls.from_wire(entity).payload for entity in batch_entities]

    def to_wire(self) -> Dict[str, Any]:
        return {"id": self.id, "payload": dict(self.payload)}


__all__ = ["BacktestJob"]
