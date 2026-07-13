"""entity_based 子进程内业务阶段耗时（写入 payload，由 engine 合并进 JobReport）。"""
from __future__ import annotations

import time
from typing import Any, Dict

ENUM_PERF_PAYLOAD_KEY = "_enum_perf"


class EnumJobPerfRecorder:
    """在 enumerator worker 内记录 load / enumerate / flush 等阶段。"""

    def __init__(self, payload: Dict[str, Any]) -> None:
        if ENUM_PERF_PAYLOAD_KEY not in payload:
            payload[ENUM_PERF_PAYLOAD_KEY] = {"phases": {}}
        self._phases: Dict[str, float] = payload[ENUM_PERF_PAYLOAD_KEY]["phases"]
        self._timers: Dict[str, float] = {}

    @classmethod
    def attach(cls, payload: Dict[str, Any]) -> "EnumJobPerfRecorder":
        return cls(payload)

    def begin(self, phase: str) -> None:
        self._timers[str(phase)] = time.perf_counter()

    def end(self, phase: str) -> float:
        key = str(phase)
        started = self._timers.pop(key, None)
        if started is None:
            return 0.0
        elapsed = max(0.0, time.perf_counter() - started)
        self._phases[key] = elapsed
        return elapsed

    def record(self, phase: str, seconds: float) -> None:
        self._phases[str(phase)] = max(0.0, float(seconds))


__all__ = ["ENUM_PERF_PAYLOAD_KEY", "EnumJobPerfRecorder"]
