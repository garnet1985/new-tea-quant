from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MergeResult:
    """Result of contract.merge / contract.extend."""

    added_rows: int
    total_rows: int
