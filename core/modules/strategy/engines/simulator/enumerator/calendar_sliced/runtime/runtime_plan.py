#!/usr/bin/env python3
"""Job 内运行时 plan：preload 深度动态调节（内存变量，job 结束即销毁）。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# carry + compute 当前片粗算预留（不计入 preload 片数 budget）
_DEFAULT_CARRY_RESERVE_MB = 128.0
_DEFAULT_COMPUTE_SLICE_RESERVE_MB = 64.0
_BUDGET_TIGHT_RATIO = 0.90
_BUDGET_LOOSE_RATIO = 0.70


@dataclass
class SliceTimingSample:
    slice_index: int
    load_sec: float = 0.0
    compute_sec: float = 0.0
    rss_after_mb: float = 0.0
    payload_bytes: int = 0


@dataclass
class CalendarSliceRuntimePlan:
    """orchestrator 持有的可变 plan；ideal_preload_ceiling 为本 job 回升上限。"""

    slice_open_days: int
    memory_budget_mb: float
    reader_workers: int
    ideal_preload_ceiling: int
    current_preload_depth: int
    queue_capacity: int
    mb_per_slice: float  # 单片 preload 体积（MB）；由 payload 滚动中位数估算
    prefetch_enabled: bool = True
    carry_reserve_mb: float = _DEFAULT_CARRY_RESERVE_MB
    compute_reserve_mb: float = _DEFAULT_COMPUTE_SLICE_RESERVE_MB
    baseline_rss_mb: float = 0.0
    calendar_progress_total: int = 0
    calendar_slice_count: int = 0
    _samples: list[SliceTimingSample] = field(default_factory=list, repr=False)

    @property
    def ahead_limit(self) -> int:
        """orchestrator dispatch 门控：与 current_preload_depth 一致。"""
        if not self.prefetch_enabled:
            return 1
        return max(1, self.current_preload_depth)

    def record_slice(
        self,
        *,
        slice_index: int,
        load_sec: float,
        compute_sec: float,
        rss_after_mb: float,
        payload_bytes: int = 0,
    ) -> None:
        self._samples.append(
            SliceTimingSample(
                slice_index=slice_index,
                load_sec=max(0.0, load_sec),
                compute_sec=max(0.0, compute_sec),
                rss_after_mb=max(0.0, rss_after_mb),
                payload_bytes=max(0, int(payload_bytes or 0)),
            )
        )
        if payload_bytes > 0:
            recent = self._samples[-3:]
            sizes_mb = [
                s.payload_bytes / (1024.0 * 1024.0)
                for s in recent
                if s.payload_bytes > 0
            ]
            if sizes_mb:
                sizes_mb.sort()
                self.mb_per_slice = max(1.0, sizes_mb[len(sizes_mb) // 2])
        elif load_sec > 0 and rss_after_mb > 0:
            # fallback：无 payload 时用 RSS 增量粗估
            recent = self._samples[-3:]
            deltas = [
                max(s.rss_after_mb - self.baseline_rss_mb, 1.0)
                for s in recent
                if s.rss_after_mb > 0
            ]
            if deltas:
                deltas.sort()
                self.mb_per_slice = deltas[len(deltas) // 2]

    def refine_from_timings(self) -> None:
        """首片/次片完成后用实测 T_io/T_compute 收紧 ideal ceiling。"""
        if not self._samples:
            return
        loads = [s.load_sec for s in self._samples if s.load_sec > 0]
        computes = [s.compute_sec for s in self._samples if s.compute_sec > 0]
        if not loads:
            return
        t_io = sum(loads) / len(loads)
        t_compute = (sum(computes) / len(computes)) if computes else 0.05
        from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.planner import (
            ideal_preload_from_timings,
            preload_depth_from_memory,
        )

        io_ideal = ideal_preload_from_timings(t_io, t_compute)
        mem_ideal = preload_depth_from_memory(
            memory_budget_mb=self.memory_budget_mb,
            mb_per_slice=self.mb_per_slice,
            carry_reserve_mb=self.carry_reserve_mb,
            compute_reserve_mb=self.compute_reserve_mb,
        )
        new_ceiling = max(1, min(io_ideal, mem_ideal, self.queue_capacity))
        if new_ceiling < self.ideal_preload_ceiling:
            self.ideal_preload_ceiling = new_ceiling
        if self.current_preload_depth > self.ideal_preload_ceiling:
            self.current_preload_depth = self.ideal_preload_ceiling

    def adjust_preload_after_slice(self, *, job_rss_mb: float) -> None:
        """每片 SliceDone 后采样一次，调节 current_preload_depth。"""
        if not self.prefetch_enabled:
            return
        budget = max(self.memory_budget_mb, 1.0)
        usage_ratio = job_rss_mb / budget
        if usage_ratio >= _BUDGET_TIGHT_RATIO:
            before = self.current_preload_depth
            # 按 mb_per_slice 估算应减几片（至少减 1）
            excess_mb = max(0.0, job_rss_mb - budget * _BUDGET_TIGHT_RATIO)
            drop = max(1, int(excess_mb / max(self.mb_per_slice, 1.0)))
            self.current_preload_depth = max(1, self.current_preload_depth - drop)
            if self.current_preload_depth < before:
                logger.warning(
                    "[calendar_slice:plan] preload %s→%s (rss=%.0fMB budget=%.0fMB)",
                    before,
                    self.current_preload_depth,
                    job_rss_mb,
                    budget,
                )
        elif (
            usage_ratio <= _BUDGET_LOOSE_RATIO
            and self.current_preload_depth < self.ideal_preload_ceiling
        ):
            before = self.current_preload_depth
            self.current_preload_depth = min(
                self.ideal_preload_ceiling,
                self.current_preload_depth + 1,
            )
            if self.current_preload_depth > before:
                logger.info(
                    "[calendar_slice:plan] preload %s→%s (rss=%.0fMB budget=%.0fMB)",
                    before,
                    self.current_preload_depth,
                    job_rss_mb,
                    budget,
                )

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "slice_open_days": self.slice_open_days,
            "memory_budget_mb": round(self.memory_budget_mb, 1),
            "reader_workers": self.reader_workers,
            "ideal_preload_ceiling": self.ideal_preload_ceiling,
            "current_preload_depth": self.current_preload_depth,
            "queue_capacity": self.queue_capacity,
            "mb_per_slice": round(self.mb_per_slice, 1),
            "prefetch_enabled": self.prefetch_enabled,
        }
        if self.calendar_progress_total > 0:
            out["calendar_progress_total"] = self.calendar_progress_total
        if self.calendar_slice_count > 0:
            out["calendar_slice_count"] = self.calendar_slice_count
        return out


__all__ = ["CalendarSliceRuntimePlan", "SliceTimingSample"]
