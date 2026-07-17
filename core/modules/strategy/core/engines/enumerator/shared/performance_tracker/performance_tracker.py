"""entity_based 子进程内业务阶段耗时（写入 payload，由 engine 合并进 JobReport）。"""
from __future__ import annotations

import time
from typing import Any, Dict

ENUM_PERF_PAYLOAD_KEY = "_enum_perf"


class EnumJobPerfRecorder:
    """enumerator worker 内业务阶段耗时（entity / slice 共用）。

    边界:
    - 负责: load / enumerate / flush 等 phase 计时写入 payload
    - 不负责: 汇总 performance.json（ProfilerReport）
    - 调用方: JobExecutor / JobBundleLoader / TimelineHooks
    """

    def __init__(self, payload: Dict[str, Any]) -> None:
        if ENUM_PERF_PAYLOAD_KEY not in payload:
            payload[ENUM_PERF_PAYLOAD_KEY] = {"phases": {}, "storage": {}, "contract": {}}
        bucket = payload[ENUM_PERF_PAYLOAD_KEY]
        if "phases" not in bucket:
            bucket["phases"] = {}
        if "storage" not in bucket:
            bucket["storage"] = {}
        if "contract" not in bucket:
            bucket["contract"] = {}
        self._root: Dict[str, Any] = bucket
        self._phases: Dict[str, float] = bucket["phases"]
        self._storage: Dict[str, Any] = bucket["storage"]
        self._contract: Dict[str, Any] = bucket["contract"]
        self._timers: Dict[str, float] = {}

    @classmethod
    def attach(cls, payload: Dict[str, Any]) -> "EnumJobPerfRecorder":
        return cls(payload)

    def begin(self, phase: str) -> None:
        self._timers[str(phase)] = time.perf_counter()

    def end(self, phase: str, *, accumulate: bool = False) -> float:
        key = str(phase)
        started = self._timers.pop(key, None)
        if started is None:
            return 0.0
        elapsed = max(0.0, time.perf_counter() - started)
        if accumulate:
            self._phases[key] = float(self._phases.get(key) or 0.0) + elapsed
        else:
            self._phases[key] = elapsed
        return elapsed

    def record(self, phase: str, seconds: float, *, accumulate: bool = False) -> None:
        key = str(phase)
        value = max(0.0, float(seconds))
        if accumulate:
            self._phases[key] = float(self._phases.get(key) or 0.0) + value
        else:
            self._phases[key] = value

    def record_storage_load(self, slot: str, seconds: float) -> None:
        elapsed = max(0.0, float(seconds))
        self._storage["load_calls"] = int(self._storage.get("load_calls") or 0) + 1
        self._storage["load_time_seconds"] = float(
            self._storage.get("load_time_seconds") or 0.0
        ) + elapsed
        loads_by_slot = self._storage.setdefault("loads_by_slot", {})
        if not isinstance(loads_by_slot, dict):
            loads_by_slot = {}
            self._storage["loads_by_slot"] = loads_by_slot
        slot_key = str(slot)
        loads_by_slot[slot_key] = float(loads_by_slot.get(slot_key) or 0.0) + elapsed

    def record_contract_until(self, slot: str, seconds: float) -> None:
        elapsed = max(0.0, float(seconds))
        self._contract["until_calls"] = int(self._contract.get("until_calls") or 0) + 1
        self._contract["until_time_seconds"] = float(
            self._contract.get("until_time_seconds") or 0.0
        ) + elapsed
        until_by_slot = self._contract.setdefault("until_by_slot", {})
        if not isinstance(until_by_slot, dict):
            until_by_slot = {}
            self._contract["until_by_slot"] = until_by_slot
        slot_key = str(slot)
        until_by_slot[slot_key] = float(until_by_slot.get(slot_key) or 0.0) + elapsed
        self.record("enum_contract_until", elapsed, accumulate=True)

    def record_unified_until(self, seconds: float) -> None:
        elapsed = max(0.0, float(seconds))
        self._contract["unified_until_calls"] = int(
            self._contract.get("unified_until_calls") or 0
        ) + 1
        self._contract["unified_until_time_seconds"] = float(
            self._contract.get("unified_until_time_seconds") or 0.0
        ) + elapsed
        self.record("enum_pit_until_unified", elapsed, accumulate=True)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "phases": dict(self._phases),
            "storage": dict(self._storage),
            "contract": dict(self._contract),
        }


__all__ = ["ENUM_PERF_PAYLOAD_KEY", "EnumJobPerfRecorder"]
