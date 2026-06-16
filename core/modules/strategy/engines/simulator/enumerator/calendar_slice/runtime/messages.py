#!/usr/bin/env python3
"""Reader / Compute 队列消息。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Union

SHUTDOWN = "__calendar_slice_shutdown__"


@dataclass(frozen=True)
class SliceLoadRequest:
    slice_id: str
    slice_index: int
    window_start: str
    window_end: str
    open_dates: Tuple[str, ...]
    load_start: str

    @classmethod
    def from_descriptor(cls, slice_desc: Any, *, load_start: str) -> "SliceLoadRequest":
        return cls(
            slice_id=str(slice_desc.slice_id),
            slice_index=int(slice_desc.slice_index),
            window_start=str(slice_desc.window_start),
            window_end=str(slice_desc.window_end),
            open_dates=tuple(slice_desc.open_dates),
            load_start=str(load_start),
        )


@dataclass(frozen=True)
class SlicePayload:
    slice_id: str
    slice_index: int
    window_start: str
    window_end: str
    open_dates: Tuple[str, ...]
    batch_transfer: Dict[str, Any]
    load_elapsed_ms: float = 0.0


@dataclass(frozen=True)
class SliceDone:
    slice_index: int
    slice_id: str
    load_elapsed_ms: float = 0.0
    compute_elapsed_ms: float = 0.0


@dataclass
class FinalizeDone:
    stock_results: List[Dict[str, Any]] = field(default_factory=list)
    calendar_progress: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LaneError:
    lane: str
    message: str
    slice_index: int = -1


LaneMessage = Union[
    str,
    SliceLoadRequest,
    SlicePayload,
    SliceDone,
    FinalizeDone,
    LaneError,
]


def is_shutdown(msg: Any) -> bool:
    return msg is SHUTDOWN or msg == SHUTDOWN


__all__ = [
    "FinalizeDone",
    "LaneError",
    "LaneMessage",
    "SHUTDOWN",
    "SliceDone",
    "SliceLoadRequest",
    "SlicePayload",
    "is_shutdown",
]
