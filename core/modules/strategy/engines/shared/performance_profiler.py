#!/usr/bin/env python3
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict

import psutil

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    time_load_data: float = 0.0
    time_calculate_indicators: float = 0.0
    time_enumerate: float = 0.0
    time_serialize: float = 0.0
    time_save_csv: float = 0.0
    time_total: float = 0.0
    db_queries: int = 0
    db_query_time: float = 0.0
    file_writes: int = 0
    file_write_time: float = 0.0
    file_write_size: int = 0
    kline_count: int = 0
    opportunity_count: int = 0
    target_count: int = 0
    memory_peak: float = 0.0
    memory_start: float = 0.0
    memory_end: float = 0.0

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "PerformanceMetrics":
        time_data = payload.get("time", {}) or {}
        io_data = payload.get("io", {}) or {}
        data_stats = payload.get("data", {}) or {}
        mem_stats = payload.get("memory", {}) or {}
        return cls(
            time_load_data=time_data.get("load_data", 0.0),
            time_calculate_indicators=time_data.get("calculate_indicators", 0.0),
            time_enumerate=time_data.get("enumerate", 0.0),
            time_serialize=time_data.get("serialize", 0.0),
            time_save_csv=time_data.get("save_csv", 0.0),
            time_total=time_data.get("total", 0.0),
            db_queries=io_data.get("db_queries", 0),
            db_query_time=io_data.get("db_query_time", 0.0),
            file_writes=io_data.get("file_writes", 0),
            file_write_time=io_data.get("file_write_time", 0.0),
            file_write_size=int(
                (io_data.get("file_write_size_mb", 0.0) or 0.0) * 1024 * 1024
            ),
            kline_count=data_stats.get("kline_count", 0),
            opportunity_count=data_stats.get("opportunity_count", 0),
            target_count=data_stats.get("target_count", 0),
            memory_peak=mem_stats.get("peak_mb", 0.0),
            memory_start=mem_stats.get("start_mb", 0.0),
            memory_end=mem_stats.get("end_mb", 0.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time": {
                "load_data": self.time_load_data,
                "calculate_indicators": self.time_calculate_indicators,
                "enumerate": self.time_enumerate,
                "serialize": self.time_serialize,
                "save_csv": self.time_save_csv,
                "total": self.time_total,
            },
            "io": {
                "db_queries": self.db_queries,
                "db_query_time": self.db_query_time,
                "file_writes": self.file_writes,
                "file_write_time": self.file_write_time,
                "file_write_size_mb": self.file_write_size / (1024 * 1024),
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
        self.metrics = PerformanceMetrics()
        self.process = psutil.Process(os.getpid())
        self._timers: Dict[str, float] = {}
        self._io_counters: Dict[str, int] = defaultdict(int)
        self._io_timers: Dict[str, float] = defaultdict(float)
        self._record_memory("start")

    def _record_memory(self, stage: str):
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

    def start_timer(self, name: str):
        self._timers[name] = time.perf_counter()

    def end_timer(self, name: str) -> float:
        if name not in self._timers:
            return 0.0
        elapsed = time.perf_counter() - self._timers[name]
        del self._timers[name]
        return elapsed

    def record_db_query(self, duration: float):
        self._io_counters["db_queries"] += 1
        self._io_timers["db_query_time"] += duration

    def record_file_write(self, size_bytes: int, duration: float):
        self._io_counters["file_writes"] += 1
        self._io_timers["file_write_time"] += duration
        self._io_counters["file_write_size"] += size_bytes

    def finalize(self) -> PerformanceMetrics:
        self.metrics.db_queries = self._io_counters["db_queries"]
        self.metrics.db_query_time = self._io_timers["db_query_time"]
        self.metrics.file_writes = self._io_counters["file_writes"]
        self.metrics.file_write_time = self._io_timers["file_write_time"]
        self.metrics.file_write_size = self._io_counters["file_write_size"]
        self._record_memory("end")
        return self.metrics


class AggregateProfiler:
    def __init__(self):
        self.stock_metrics: Dict[str, PerformanceMetrics] = {}
        self.start_time = time.perf_counter()
        self.process = psutil.Process(os.getpid())
        self.start_memory = self._get_memory_mb()

    def _get_memory_mb(self) -> float:
        try:
            return self.process.memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0

    def add_stock_metrics(self, stock_id: str, metrics: PerformanceMetrics):
        self.stock_metrics[stock_id] = metrics

    def get_summary(self) -> Dict[str, Any]:
        if not self.stock_metrics:
            return {}
        total_time = time.perf_counter() - self.start_time
        end_memory = self._get_memory_mb()
        total_db_queries = sum(m.db_queries for m in self.stock_metrics.values())
        total_db_time = sum(m.db_query_time for m in self.stock_metrics.values())
        total_file_writes = sum(m.file_writes for m in self.stock_metrics.values())
        total_file_time = sum(m.file_write_time for m in self.stock_metrics.values())
        total_file_size = sum(m.file_write_size for m in self.stock_metrics.values())
        total_kline_count = sum(m.kline_count for m in self.stock_metrics.values())
        total_opp_count = sum(m.opportunity_count for m in self.stock_metrics.values())
        total_target_count = sum(m.target_count for m in self.stock_metrics.values())
        avg_time_per_stock = total_time / len(self.stock_metrics)
        avg_db_queries_per_stock = total_db_queries / len(self.stock_metrics)
        avg_memory_per_stock = sum(m.memory_peak for m in self.stock_metrics.values()) / len(self.stock_metrics)
        return {
            "summary": {
                "total_stocks": len(self.stock_metrics),
                "total_time_seconds": total_time,
                "total_time_minutes": total_time / 60,
                "avg_time_per_stock_seconds": avg_time_per_stock,
            },
            "io": {
                "total_db_queries": total_db_queries,
                "avg_db_queries_per_stock": avg_db_queries_per_stock,
                "total_db_time_seconds": total_db_time,
                "avg_db_time_per_query_ms": (total_db_time / total_db_queries * 1000) if total_db_queries > 0 else 0,
                "total_file_writes": total_file_writes,
                "total_file_size_mb": total_file_size / (1024 * 1024),
                "total_file_time_seconds": total_file_time,
            },
            "data": {
                "total_kline_count": total_kline_count,
                "total_opportunity_count": total_opp_count,
                "total_target_count": total_target_count,
                "avg_opportunities_per_stock": total_opp_count / len(self.stock_metrics) if self.stock_metrics else 0,
            },
            "memory": {
                "start_mb": self.start_memory,
                "end_mb": end_memory,
                "delta_mb": end_memory - self.start_memory,
                "avg_peak_per_stock_mb": avg_memory_per_stock,
            },
            "time_breakdown": {
                "avg_load_data_ms": sum(m.time_load_data for m in self.stock_metrics.values()) / len(self.stock_metrics) * 1000,
                "avg_enumerate_ms": sum(m.time_enumerate for m in self.stock_metrics.values()) / len(self.stock_metrics) * 1000,
                "avg_serialize_ms": sum(m.time_serialize for m in self.stock_metrics.values()) / len(self.stock_metrics) * 1000,
            },
        }

    def print_report(self):
        summary = self.get_summary()
        if not summary:
            logger.info("no performance data")
            return
        logger.info("📊 Performance summary: %s", summary.get("summary"))


__all__ = ["PerformanceMetrics", "PerformanceProfiler", "AggregateProfiler"]
