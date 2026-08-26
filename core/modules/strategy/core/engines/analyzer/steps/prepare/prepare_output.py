"""Prepare step deliverable."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PrepareOutput:
    """Data-prep output — ``analysis/source.json`` on disk."""

    source_path: Path
    analysis_dir: Path
    entity_count: int
    investment_count: int
    step: str
    version_id: str

    @classmethod
    def from_payload(
        cls,
        *,
        source_path: Path,
        payload: Dict[str, Any],
    ) -> "PrepareOutput":
        entity_count = len(payload.get("entities") or [])
        investment_count = int(
            (payload.get("inputs") or {})
            .get("capture", {})
            .get("coverage", {})
            .get("investment_count", 0)
        )
        return cls(
            source_path=Path(source_path),
            analysis_dir=Path(source_path).parent,
            entity_count=entity_count,
            investment_count=investment_count,
            step=str(payload.get("step") or ""),
            version_id=str(payload.get("version_id") or ""),
        )
