#!/usr/bin/env python3
"""
回测 / 枚举性能剖析（schema v2）。

每股 ``performance_metrics`` 与 ``0_performance_report.json``（聚合）使用同一 schema：
- ``time``：墙钟（秒）
- ``storage``：contract.load 累计（读库 / Parquet / 文件）
- ``file_io``：结果写盘
- 聚合层另含 ``summary``、``time_breakdown.pct_of_worker_total``
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

import psutil

logger = logging.getLogger(__name__)

REPORT_SCHEMA_VERSION = 2


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


WORKER_PHASE_KEYS = (
    "load_contracts",
    "calculate_indicators",
    "build_cursor",
    "load_extras",
    "enumerate",
    "serialize",
    "save_csv",
)


def _worker_phase_seconds(metrics: "PerformanceMetrics") -> Dict[str, float]:
    return {
        "load_contracts": metrics.time_load_contracts,
        "calculate_indicators": metrics.time_calculate_indicators,
        "build_cursor": metrics.time_build_cursor,
        "load_extras": metrics.time_load_extras,
        "enumerate": metrics.time_enumerate,
        "serialize": metrics.time_serialize,
        "save_csv": metrics.time_save_csv,
    }


def _sum_phases(metrics: "PerformanceMetrics") -> float:
    return sum(_worker_phase_seconds(metrics).values())


@dataclass
class PerformanceMetrics:
    stock_id: str = ""
    time_load_data: float = 0.0
    time_load_contracts: float = 0.0
    time_calculate_indicators: float = 0.0
    time_build_cursor: float = 0.0
    time_load_extras: float = 0.0
    time_enumerate: float = 0.0
    time_serialize: float = 0.0
    time_save_csv: float = 0.0
    time_total: float = 0.0
    storage_load_calls: int = 0
    storage_load_time: float = 0.0
    storage_loads_by_slot: Dict[str, float] = field(default_factory=dict)
    file_writes: int = 0
    file_write_time: float = 0.0
    file_write_size: int = 0
    kline_count: int = 0
    opportunity_count: int = 0
    target_count: int = 0
    memory_peak: float = 0.0
    memory_start: float = 0.0
    memory_end: float = 0.0
    load_path: str = ""
    skipped_short_data: bool = False

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "PerformanceMetrics":
        if not payload or int(payload.get("schema_version") or 0) != REPORT_SCHEMA_VERSION:
            return cls()
        time_data = payload.get("time") or {}
        storage = payload.get("storage") or {}
        file_io = payload.get("file_io") or {}
        data_stats = payload.get("data") or {}
        mem_stats = payload.get("memory") or {}
        return cls(
            stock_id=str(payload.get("stock_id") or ""),
            time_load_data=float(time_data.get("load_data") or 0.0),
            time_load_contracts=float(time_data.get("load_contracts") or 0.0),
            time_calculate_indicators=float(time_data.get("calculate_indicators") or 0.0),
            time_build_cursor=float(time_data.get("build_cursor") or 0.0),
            time_load_extras=float(time_data.get("load_extras") or 0.0),
            time_enumerate=float(time_data.get("enumerate") or 0.0),
            time_serialize=float(time_data.get("serialize") or 0.0),
            time_save_csv=float(time_data.get("save_csv") or 0.0),
            time_total=float(time_data.get("total") or 0.0),
            storage_load_calls=int(storage.get("load_calls") or 0),
            storage_load_time=float(storage.get("load_time_seconds") or 0.0),
            storage_loads_by_slot=dict(storage.get("loads_by_slot") or {}),
            file_writes=int(file_io.get("writes") or 0),
            file_write_time=float(file_io.get("write_time_seconds") or 0.0),
            file_write_size=int(float(file_io.get("write_size_mb") or 0.0) * 1024 * 1024),
            kline_count=int(data_stats.get("kline_count") or 0),
            opportunity_count=int(data_stats.get("opportunity_count") or 0),
            target_count=int(data_stats.get("target_count") or 0),
            memory_peak=float(mem_stats.get("peak_mb") or 0.0),
            memory_start=float(mem_stats.get("start_mb") or 0.0),
            memory_end=float(mem_stats.get("end_mb") or 0.0),
            load_path=str(payload.get("load_path") or ""),
            skipped_short_data=bool(payload.get("skipped_short_data", False)),
        )

    def to_dict(self) -> Dict[str, Any]:
        phase_sum = _sum_phases(self)
        return {
            "schema_version": REPORT_SCHEMA_VERSION,
            "stock_id": self.stock_id,
            "load_path": self.load_path,
            "skipped_short_data": self.skipped_short_data,
            "time": {
                "total": self.time_total,
                "load_data": self.time_load_data,
                "load_contracts": self.time_load_contracts,
                "calculate_indicators": self.time_calculate_indicators,
                "build_cursor": self.time_build_cursor,
                "load_extras": self.time_load_extras,
                "enumerate": self.time_enumerate,
                "serialize": self.time_serialize,
                "save_csv": self.time_save_csv,
                "unaccounted": max(0.0, self.time_total - phase_sum),
            },
            "storage": {
                "load_calls": self.storage_load_calls,
                "load_time_seconds": self.storage_load_time,
                "loads_by_slot": dict(self.storage_loads_by_slot),
            },
            "file_io": {
                "writes": self.file_writes,
                "write_time_seconds": self.file_write_time,
                "write_size_mb": self.file_write_size / (1024 * 1024),
            },
            "data": {
                "kline_count": self.kline_count,
                "opportunity_count": self.opportunity_count,
                "target_count": self.target_count,
            },
            "memory": {
                "peak_mb": self.memory_peak,
                "start_mb": self.memory_start,
                "end_mb": self.memory_end,
                "delta_mb": self.memory_end - self.memory_start,
            },
        }


class PerformanceProfiler:
    def __init__(self, stock_id: str):
        self.stock_id = stock_id
        self.metrics = PerformanceMetrics(stock_id=stock_id)
        self.process = psutil.Process(os.getpid())
        self._timers: Dict[str, float] = {}
        self._record_memory("start")

    def _record_memory(self, stage: str) -> None:
        try:
            mem_mb = self.process.memory_info().rss / (1024 * 1024)
            if stage == "start":
                self.metrics.memory_start = mem_mb
            elif stage == "end":
                self.metrics.memory_end = mem_mb
            if mem_mb > self.metrics.memory_peak:
                self.metrics.memory_peak = mem_mb
        except Exception:
            pass

    def start_timer(self, name: str) -> None:
        self._timers[name] = time.perf_counter()

    def end_timer(self, name: str) -> float:
        if name not in self._timers:
            return 0.0
        elapsed = time.perf_counter() - self._timers[name]
        del self._timers[name]
        return elapsed

    def record_storage_load(self, slot: str, duration: float) -> None:
        duration = max(0.0, float(duration))
        self.metrics.storage_load_calls += 1
        self.metrics.storage_load_time += duration
        key = str(slot or "unknown")
        self.metrics.storage_loads_by_slot[key] = (
            self.metrics.storage_loads_by_slot.get(key, 0.0) + duration
        )

    def record_file_write(self, size_bytes: int, duration: float) -> None:
        self.metrics.file_writes += 1
        self.metrics.file_write_time += max(0.0, float(duration))
        self.metrics.file_write_size += max(0, int(size_bytes))

    def finalize(self) -> PerformanceMetrics:
        self._record_memory("end")
        return self.metrics


def _aggregate_avg_ms(values: List[float]) -> float:
    if not values:
        return 0.0
    return (sum(values) / len(values)) * 1000.0


def _aggregate_pct_of_worker_total(metrics_list: List[PerformanceMetrics]) -> Dict[str, float]:
    totals = {k: 0.0 for k in WORKER_PHASE_KEYS}
    grand = 0.0
    for m in metrics_list:
        phases = _worker_phase_seconds(m)
        for k, v in phases.items():
            totals[k] += v
        grand += _sum_phases(m) or m.time_total
    if grand <= 0:
        return {k: 0.0 for k in totals}
    return {k: round(_safe_div(v, grand) * 100.0, 2) for k, v in totals.items()}


def _dominant_phase(pct_map: Dict[str, float]) -> str:
    if not pct_map:
        return ""
    return max(pct_map.items(), key=lambda item: item[1])[0]


class AggregateProfiler:
    def __init__(self) -> None:
        self.stock_metrics: Dict[str, PerformanceMetrics] = {}
        self.start_time = time.perf_counter()
        self.process = psutil.Process(os.getpid())
        self.start_memory = self._get_memory_mb()
        # 运行时元数据（由 flow 层注入）
        self._runtime_context: Dict[str, Any] = {}
        # 额外数据（如 calendar_slice_runtime_plan，由 services 层注入）
        self._extra_data: Dict[str, Any] = {}

    def set_runtime_context(self, **kwargs: Any) -> None:
        """注入运行时元数据（execution_mode, max_workers, db_engine 等）。"""
        self._runtime_context.update(kwargs)

    def set_extra_data(self, **kwargs: Any) -> None:
        """注入额外数据（如 calendar_slice_runtime_plan）。"""
        self._extra_data.update(kwargs)

    def _get_memory_mb(self) -> float:
        try:
            return self.process.memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0

    def add_stock_metrics(self, stock_id: str, metrics: PerformanceMetrics) -> None:
        self.stock_metrics[str(stock_id)] = metrics

    def get_summary(self) -> Dict[str, Any]:
        if not self.stock_metrics:
            return {}
        wall_seconds = time.perf_counter() - self.start_time
        end_memory = self._get_memory_mb()
        metrics_list = list(self.stock_metrics.values())
        n = len(metrics_list)

        total_storage_calls = sum(m.storage_load_calls for m in metrics_list)
        total_storage_time = sum(m.storage_load_time for m in metrics_list)
        total_file_writes = sum(m.file_writes for m in metrics_list)
        total_file_time = sum(m.file_write_time for m in metrics_list)
        total_file_size = sum(m.file_write_size for m in metrics_list)
        sum_worker_total = sum(m.time_total for m in metrics_list)
        short_data_count = sum(1 for m in metrics_list if m.skipped_short_data)

        pct_worker = _aggregate_pct_of_worker_total(metrics_list)
        dominant = _dominant_phase(pct_worker)

        worker_phase_sums = {
            "load_contracts": sum(m.time_load_contracts for m in metrics_list),
            "calculate_indicators": sum(m.time_calculate_indicators for m in metrics_list),
            "build_cursor": sum(m.time_build_cursor for m in metrics_list),
            "load_extras": sum(m.time_load_extras for m in metrics_list),
            "enumerate": sum(m.time_enumerate for m in metrics_list),
            "serialize": sum(m.time_serialize for m in metrics_list),
            "save_csv": sum(m.time_save_csv for m in metrics_list),
            "total": sum_worker_total,
        }

        return {
            "schema_version": REPORT_SCHEMA_VERSION,
            "report_kind": "aggregate",
            "interpretation": {
                "wall_clock_seconds": "父进程墙钟（多进程并行时通常小于 worker_phase_sums.total）",
                "worker_phase_sums_seconds": "各子进程阶段时间之和，可大于墙钟",
                "storage.load_time_seconds": "各股 storage.load 墙钟之和",
                "time_breakdown.pct_of_worker_total": "单股 worker 时间内各阶段占比，用于判断读数据 vs 策略循环",
            },
            "summary": {
                "total_stocks": n,
                "wall_clock_seconds": wall_seconds,
                "wall_clock_minutes": wall_seconds / 60,
                "avg_wall_clock_per_stock_seconds": wall_seconds / n,
                "sum_worker_total_seconds": sum_worker_total,
                "parallelism_factor": round(_safe_div(sum_worker_total, wall_seconds), 2),
                "stocks_skipped_short_data": short_data_count,
            },
            "storage": {
                "total_load_calls": total_storage_calls,
                "avg_load_calls_per_stock": total_storage_calls / n,
                "sum_load_time_seconds": total_storage_time,
                "avg_load_time_per_stock_seconds": total_storage_time / n,
                "avg_load_time_per_call_ms": (
                    (total_storage_time / total_storage_calls) * 1000
                    if total_storage_calls
                    else 0.0
                ),
            },
            "file_io": {
                "total_writes": total_file_writes,
                "sum_write_time_seconds": total_file_time,
                "sum_write_size_mb": total_file_size / (1024 * 1024),
            },
            "data": {
                "total_kline_count": sum(m.kline_count for m in metrics_list),
                "total_opportunity_count": sum(m.opportunity_count for m in metrics_list),
                "total_target_count": sum(m.target_count for m in metrics_list),
                "avg_opportunities_per_stock": sum(m.opportunity_count for m in metrics_list) / n,
            },
            "memory": {
                "parent_start_mb": self.start_memory,
                "parent_end_mb": end_memory,
                "parent_delta_mb": end_memory - self.start_memory,
                "avg_peak_per_stock_mb": sum(m.memory_peak for m in metrics_list) / n,
            },
            "time_breakdown": {
                "avg_load_data_ms": _aggregate_avg_ms([m.time_load_data for m in metrics_list]),
                "avg_load_contracts_ms": _aggregate_avg_ms([m.time_load_contracts for m in metrics_list]),
                "avg_calculate_indicators_ms": _aggregate_avg_ms(
                    [m.time_calculate_indicators for m in metrics_list]
                ),
                "avg_build_cursor_ms": _aggregate_avg_ms([m.time_build_cursor for m in metrics_list]),
                "avg_load_extras_ms": _aggregate_avg_ms([m.time_load_extras for m in metrics_list]),
                "avg_enumerate_ms": _aggregate_avg_ms([m.time_enumerate for m in metrics_list]),
                "avg_serialize_ms": _aggregate_avg_ms([m.time_serialize for m in metrics_list]),
                "avg_save_csv_ms": _aggregate_avg_ms([m.time_save_csv for m in metrics_list]),
                "avg_total_per_stock_ms": _aggregate_avg_ms([m.time_total for m in metrics_list]),
                "pct_of_worker_total": pct_worker,
                "dominant_phase": dominant,
            },
            "worker_phase_sums_seconds": worker_phase_sums,
            "runtime": dict(self._runtime_context),
            **self._extra_data,  # 注入额外数据（如 calendar_slice_runtime_plan）
        }

    def print_report(self) -> None:
        summary = self.get_summary()
        if not summary:
            logger.info("no performance data")
            return
        s = summary.get("summary") or {}
        tb = summary.get("time_breakdown") or {}
        pct = tb.get("pct_of_worker_total") or {}
        storage = summary.get("storage") or {}
        logger.info(
            "📊 perf wall=%.1fs stocks=%s parallelism=%.2fx dominant=%s "
            "load_contracts=%.1f%% enumerate=%.1f%% storage_load_sum=%.1fs",
            float(s.get("wall_clock_seconds") or 0),
            s.get("total_stocks"),
            float(s.get("parallelism_factor") or 0),
            tb.get("dominant_phase"),
            float(pct.get("load_contracts") or 0),
            float(pct.get("enumerate") or 0),
            float(storage.get("sum_load_time_seconds") or 0),
        )


__all__ = [
    "REPORT_SCHEMA_VERSION",
    "PerformanceMetrics",
    "PerformanceProfiler",
    "AggregateProfiler",
]
