"""BacktestEngine execution mode enum (shared by facade, pipelines, job validation)."""
from __future__ import annotations

from enum import Enum
from typing import Union


class BacktestMode(str, Enum):
    """Backtest execution mode."""

    ENTITY_BASED = "entity_based"
    SLICE_BASED = "slice_based"

    @classmethod
    def normalize(cls, mode: Union[str, BacktestMode]) -> str:
        if isinstance(mode, cls):
            return mode.value
        raw = str(mode or "").strip().lower()
        if raw == cls.ENTITY_BASED.value:
            return raw
        if raw == cls.SLICE_BASED.value:
            return raw
        raise ValueError(f"unknown backtest mode: {mode!r}")


__all__ = ["BacktestMode"]
