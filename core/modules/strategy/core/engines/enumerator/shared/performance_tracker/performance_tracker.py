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
    - 调用方: JobExecutor / JobBundleLoader / EntityTaskState / SliceTaskState
    """

    def __init__(self, payload: Dict[str, Any]) -> None:
        if ENUM_PERF_PAYLOAD_KEY not in payload:
            payload[ENUM_PERF_PAYLOAD_KEY] = {
                "phases": {},
                "storage": {},
                "contract": {},
                "calendar": {},
            }
        bucket = payload[ENUM_PERF_PAYLOAD_KEY]
        if "phases" not in bucket:
            bucket["phases"] = {}
        if "storage" not in bucket:
            bucket["storage"] = {}
        if "contract" not in bucket:
            bucket["contract"] = {}
        if "calendar" not in bucket:
            bucket["calendar"] = {}
        self._root: Dict[str, Any] = bucket
        self._phases: Dict[str, float] = bucket["phases"]
        self._storage: Dict[str, Any] = bucket["storage"]
        self._contract: Dict[str, Any] = bucket["contract"]
        self._calendar: Dict[str, Any] = bucket["calendar"]
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

    def set_calendar_meta(
        self,
        *,
        open_dates_count: int,
        period_start: str = "",
        period_end: str = "",
        entities_in_job: int = 0,
    ) -> None:
        """记录本 job 日历窗口元信息（沉默成本分母）。"""
        self._calendar["open_dates_count"] = int(open_dates_count)
        self._calendar["period_start"] = str(period_start or "")
        self._calendar["period_end"] = str(period_end or "")
        self._calendar["entities_in_job"] = int(entities_in_job)

    def record_calendar_day(
        self,
        *,
        any_bar: bool,
        bar_hits: int,
        bar_misses: int,
        pit_sec: float = 0.0,
        skipped_before_ready: bool = False,
    ) -> None:
        """按日累计 bar 命中/空转，并把 pit 耗时拆到 empty / active。"""
        self._calendar["days_total"] = int(self._calendar.get("days_total") or 0) + 1
        hits = max(0, int(bar_hits))
        misses = max(0, int(bar_misses))
        self._calendar["entity_day_bar_hit"] = (
            int(self._calendar.get("entity_day_bar_hit") or 0) + hits
        )
        self._calendar["entity_day_bar_miss"] = (
            int(self._calendar.get("entity_day_bar_miss") or 0) + misses
        )
        if skipped_before_ready:
            self._calendar["days_skipped_before_ready"] = (
                int(self._calendar.get("days_skipped_before_ready") or 0) + 1
            )
        elapsed = max(0.0, float(pit_sec))
        if any_bar:
            self._calendar["days_with_any_bar"] = (
                int(self._calendar.get("days_with_any_bar") or 0) + 1
            )
            self._calendar["pit_active_day_sec"] = (
                float(self._calendar.get("pit_active_day_sec") or 0.0) + elapsed
            )
        else:
            self._calendar["days_all_empty"] = (
                int(self._calendar.get("days_all_empty") or 0) + 1
            )
            self._calendar["pit_empty_day_sec"] = (
                float(self._calendar.get("pit_empty_day_sec") or 0.0) + elapsed
            )

    def snapshot(self) -> Dict[str, Any]:
        return {
            "phases": dict(self._phases),
            "storage": dict(self._storage),
            "contract": dict(self._contract),
            "calendar": dict(self._calendar),
        }


__all__ = ["ENUM_PERF_PAYLOAD_KEY", "EnumJobPerfRecorder"]
