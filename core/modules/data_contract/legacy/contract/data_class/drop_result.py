from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DropResult:
    """Result of contract.drop — prefix rows released from memory."""

    dropped_rows: int
    total_rows: int
