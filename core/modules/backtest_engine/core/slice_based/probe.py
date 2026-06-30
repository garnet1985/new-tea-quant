"""
Backtest Engine - Slice-based Probe

Calendar-slice dispatch probe: in-process orchestrator sample + runtime plan metrics.
"""
from __future__ import annotations

import copy
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.backtest_engine.core.shared.machine_info import MachineCapacity
from core.modules.backtest_engine.core.shared.types import JobContext

logger = logging.getLogger(__name__)

DEFAULT_PROBE_SLICE_COUNT: int = 2
DEFAULT_PROBE_SLICE_OPEN_DAYS: int = 5
DEFAULT_PROBE_ENTITY_COUNT: int = 3
DEFAULT_PROBE_SAFETY_FACTOR: float = 1.25

PROBE_EXECUTOR_TAG = "tag"
PROBE_EXECUTOR_STRATEGY_ENUM = "strategy.enum"



@dataclass(frozen=True)
class SliceProbeResult:
    """切片探针结果。"""

    mb_per_slice_reader: float
    mb_per_slice_compute: float
    mb_per_slice_payload: float
    sec_per_slice_reader: float
    sec_per_slice_compute: float
    slices_sampled: int
    wall_sec: float
    peak_rss_mb_reader: float
    peak_rss_mb_compute: float


class SliceProbe:
    """Calendar-slice dispatch probe."""

    @staticmethod
    def should_run(
        jobs: List[Dict[str, Any]],
        performance: Dict[str, Any],
    ) -> bool:
        if performance.get("slice_probe") is False:
            return False
        if performance.get("dispatch_probe") is False:
            return False
        if (
            performance.get("reader_workers") not in (None, "", "auto")
            and performance.get("queue_capacity") not in (None, "", "auto")
            and performance.get("queue_depth") not in (None, "", "auto")
        ):
            return False
        if performance.get("mb_per_slice_staged") not in (None, ""):
            return False
        if not jobs:
            return False
        payload = BacktestJob.from_dict(jobs[0]).payload
        if not SliceProbe._resolve_open_dates(payload):
            return False
        if not (payload.get("entity_ids") or payload.get("stock_ids")):
            return False
        if not payload.get("worker_module_path"):
            return False
        return True

    @staticmethod
    def build_probe_jobs(
        jobs: List[Dict[str, Any]],
        capacity: MachineCapacity,
        performance: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        _ = capacity
        if not jobs:
            return []

        probe_payload = SliceProbe.build_probe_payload(jobs, performance)
        job_id = str(probe_payload.pop("_probe_job_id", "slice_probe"))
        return [{"id": job_id, "payload": probe_payload}]

    @staticmethod
    def build_probe_payload(
        jobs: List[Dict[str, Any]],
        performance: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build a truncated bulk calendar_slice payload for probe."""
        parsed = BacktestJob.from_dict(jobs[0])
        job_id, payload = parsed.id, parsed.payload
        probe = copy.deepcopy(payload)

        probe_slice_count = max(1, int(performance.get("probe_slice_count", DEFAULT_PROBE_SLICE_COUNT)))
        probe_slice_open_days = max(
            1,
            int(performance.get("probe_slice_open_days", DEFAULT_PROBE_SLICE_OPEN_DAYS)),
        )
        probe_entity_count = max(
            1,
            int(performance.get("probe_entity_count", DEFAULT_PROBE_ENTITY_COUNT)),
        )

        probe["_slice_probe"] = True
        probe["_probe_max_slices"] = probe_slice_count
        probe["_probe_slice_open_days"] = probe_slice_open_days
        probe["slice_open_days"] = "auto"
        probe["_probe_job_id"] = f"{job_id}_probe"

        entity_ids = list(probe.get("entity_ids") or [])
        if entity_ids:
            probe["entity_ids"] = entity_ids[:probe_entity_count]
            entities = probe.get("entities")
            if isinstance(entities, list):
                probe["entities"] = entities[:probe_entity_count]

        stock_ids = list(probe.get("stock_ids") or [])
        if stock_ids:
            probe["stock_ids"] = stock_ids[:probe_entity_count]

        needed_open_days = probe_slice_count * probe_slice_open_days
        open_dates = SliceProbe._resolve_open_dates(probe)
        if open_dates:
            truncated = open_dates[:needed_open_days]
            probe["open_dates"] = truncated
            calendar = probe.get("backtest_calendar")
            if isinstance(calendar, dict):
                calendar = dict(calendar)
                calendar["open_dates"] = truncated
                if truncated:
                    calendar["start_date"] = truncated[0]
                    calendar["end_date"] = truncated[-1]
                probe["backtest_calendar"] = calendar
            if truncated:
                probe["start_date"] = truncated[0]
                probe["end_date"] = truncated[-1]

        logger.info(
            "Slice探针payload: job=%s slices=%s slice_days=%s entities=%s open_days=%s",
            job_id,
            probe_slice_count,
            probe_slice_open_days,
            probe_entity_count,
            len(probe.get("open_dates") or []),
        )
        return probe

    @staticmethod
    def dispatch(
        probe_jobs: List[Dict[str, Any]],
        *,
        execute_fn: Optional[Callable[[JobContext], Dict[str, Any]]],
        performance: Dict[str, Any],
        log_label: str = "Slice探针",
        run_name: str = "",
    ) -> SliceProbeResult:
        if not probe_jobs:
            return SliceProbe._default_result(performance)

        if execute_fn is None:
            logger.warning("%s探针跳过：未提供 execute_fn", log_label)
            return SliceProbe._default_result(performance)

        payload = BacktestJob.from_dict(probe_jobs[0]).payload
        probe_payload = dict(payload)

        logger.info(
            "%s启动: open_days=%s",
            log_label,
            len(probe_payload.get("open_dates") or []),
        )

        raw = SliceProbe._run_probe_in_subprocess(
            execute_fn,
            probe_payload,
            run_name or f"{log_label}:probe",
            performance,
            log_label,
        )
        return SliceProbe._build_probe_result(raw, performance, log_label)

    @staticmethod
    def _run_probe_in_subprocess(
        execute_fn: Callable[[JobContext], Dict[str, Any]],
        probe_payload: Dict[str, Any],
        run_name: str,
        performance: Dict[str, Any],
        log_label: str,
    ) -> Dict[str, Any]:
        from core.infra.db.engines.duckdb.process_pool_scope import (
            is_duckdb_backend,
            is_main_duckdb_worker_pool_active,
            prepare_main_for_worker_pool,
            restore_after_worker_pool,
            wait_pool_children_done,
        )

        prepared_here = False
        if is_duckdb_backend():
            wait_pool_children_done(timeout_sec=30.0)
            if not is_main_duckdb_worker_pool_active():
                prepare_main_for_worker_pool(None)
                prepared_here = True

        try:
            raw = _slice_probe_worker((execute_fn, probe_payload, run_name))
            wait_pool_children_done(timeout_sec=15.0)
            return raw
        finally:
            if prepared_here:
                restore_after_worker_pool()

    @staticmethod
    def _build_probe_result(
        raw: Dict[str, Any],
        performance: Dict[str, Any],
        log_label: str,
    ) -> SliceProbeResult:
        safety = max(
            1.0,
            float(
                performance.get("slice_probe_safety_factor")
                or performance.get("dispatch_probe_safety_factor")
                or DEFAULT_PROBE_SAFETY_FACTOR
            ),
        )

        if not raw.get("success", True):
            raise RuntimeError(f"{log_label}探针 job 失败: {raw!r}")

        orchestrator_out = raw.get("orchestrator_result")
        if not isinstance(orchestrator_out, dict):
            raise RuntimeError(f"{log_label}探针缺少 orchestrator_result: {raw!r}")

        if not orchestrator_out.get("success", True):
            raise RuntimeError(
                f"{log_label}探针 orchestrator 失败: {orchestrator_out!r}"
            )

        metrics = SliceProbe._extract_metrics_from_plan(orchestrator_out, safety_factor=safety)
        wall_sec = float(raw.get("wall_sec") or 0.0)
        slices_sampled = int(metrics["slices_sampled"])

        result = SliceProbeResult(
            mb_per_slice_reader=float(metrics["mb_per_slice_reader"]),
            mb_per_slice_compute=float(metrics["mb_per_slice_compute"]),
            mb_per_slice_payload=float(metrics["mb_per_slice_payload"]),
            sec_per_slice_reader=float(metrics["sec_per_slice_reader"]),
            sec_per_slice_compute=float(metrics["sec_per_slice_compute"]),
            slices_sampled=slices_sampled,
            wall_sec=wall_sec,
            peak_rss_mb_reader=float(metrics["peak_rss_mb_reader"]),
            peak_rss_mb_compute=float(metrics["peak_rss_mb_compute"]),
        )

        logger.info(
            "%s完成: reader=%.1fMB/slice compute=%.1fMB/slice payload=%.1fMB/slice "
            "wall=%.2fs slices=%s",
            log_label,
            result.mb_per_slice_reader,
            result.mb_per_slice_compute,
            result.mb_per_slice_payload,
            result.wall_sec,
            result.slices_sampled,
        )
        return result

    @staticmethod
    def _extract_metrics_from_plan(
        orchestrator_result: Dict[str, Any],
        *,
        safety_factor: float,
    ) -> Dict[str, float]:
        """
        Parse ``performance_metrics.calendar_slice_runtime_plan`` probe samples.

        Derives per-slice reader / compute / payload estimates for OOM planning.
        """
        perf = orchestrator_result.get("performance_metrics") or {}
        plan = perf.get("calendar_slice_runtime_plan") or {}
        samples: List[Dict[str, Any]] = list(plan.get("slice_samples") or [])
        if not samples:
            raise RuntimeError("slice probe produced no slice_samples")

        baseline = float(plan.get("baseline_rss_mb") or 0.0)
        safety = max(1.0, float(safety_factor))

        payload_mbs = [
            float(sample.get("payload_mb") or 0.0)
            for sample in samples
            if float(sample.get("payload_mb") or 0.0) > 0.0
        ]
        payload_mb = SliceProbe._median(payload_mbs) if payload_mbs else 1.0

        loads = [
            float(sample.get("load_sec") or 0.0)
            for sample in samples
            if float(sample.get("load_sec") or 0.0) > 0.0
        ]
        computes = [
            float(sample.get("compute_sec") or 0.0)
            for sample in samples
            if float(sample.get("compute_sec") or 0.0) > 0.0
        ]
        sec_reader = sum(loads) / len(loads) if loads else 0.1
        sec_compute = sum(computes) / len(computes) if computes else 0.1

        rss_deltas = [
            max(float(sample.get("rss_after_mb") or 0.0) - baseline, 1.0)
            for sample in samples
            if float(sample.get("rss_after_mb") or 0.0) > 0.0
        ]
        rss_delta = SliceProbe._median(rss_deltas) if rss_deltas else max(payload_mb, 1.0)

        io_share = sec_reader / max(sec_reader + sec_compute, 0.001)
        total_mb = max(rss_delta, payload_mb) * safety
        peak_delta = max(rss_deltas) if rss_deltas else rss_delta

        return {
            "mb_per_slice_reader": max(0.1, total_mb * io_share),
            "mb_per_slice_compute": max(0.1, total_mb * (1.0 - io_share)),
            "mb_per_slice_payload": max(0.1, payload_mb * safety),
            "sec_per_slice_reader": sec_reader,
            "sec_per_slice_compute": sec_compute,
            "slices_sampled": float(len(samples)),
            "peak_rss_mb_reader": max(0.1, peak_delta * io_share),
            "peak_rss_mb_compute": max(0.1, peak_delta * (1.0 - io_share)),
        }

    @staticmethod
    def _median(values: List[float]) -> float:
        ordered = sorted(values)
        return ordered[len(ordered) // 2]

    @staticmethod
    def _default_result(performance: Dict[str, Any]) -> SliceProbeResult:
        staged = performance.get("mb_per_slice_staged")
        if staged not in (None, ""):
            per = max(0.1, float(staged))
            return SliceProbeResult(
                mb_per_slice_reader=per * 0.4,
                mb_per_slice_compute=per * 0.6,
                mb_per_slice_payload=per * 0.2,
                sec_per_slice_reader=0.1,
                sec_per_slice_compute=0.2,
                slices_sampled=0,
                wall_sec=0.0,
                peak_rss_mb_reader=per,
                peak_rss_mb_compute=per,
            )
        return SliceProbeResult(
            mb_per_slice_reader=10.0,
            mb_per_slice_compute=15.0,
            mb_per_slice_payload=5.0,
            sec_per_slice_reader=0.1,
            sec_per_slice_compute=0.2,
            slices_sampled=0,
            wall_sec=0.0,
            peak_rss_mb_reader=10.0,
            peak_rss_mb_compute=15.0,
        )

    @staticmethod
    def _resolve_open_dates(payload: Dict[str, Any]) -> List[str]:
        open_dates = payload.get("open_dates")
        if isinstance(open_dates, list) and open_dates:
            return [str(d) for d in open_dates if str(d).strip()]

        calendar = payload.get("backtest_calendar")
        if isinstance(calendar, dict):
            calendar_dates = calendar.get("open_dates")
            if isinstance(calendar_dates, list) and calendar_dates:
                return [str(d) for d in calendar_dates if str(d).strip()]
        return []


def _slice_probe_worker(args: tuple) -> Dict[str, Any]:
    execute_fn, probe_payload, run_name = args
    rss_before_mb = _process_rss_mb()
    t0 = time.perf_counter()
    ctx = JobContext(
        job_id=str(probe_payload.get("_job_id") or probe_payload.get("job_id") or "slice_probe"),
        payload=dict(probe_payload),
        task_name=run_name,
    )
    orchestrator_result = execute_fn(ctx)
    if not isinstance(orchestrator_result, dict):
        orchestrator_result = {"success": True, "data": orchestrator_result}
    rss_after_mb = _process_rss_mb()
    wall_sec = time.perf_counter() - t0
    return {
        "success": bool(orchestrator_result.get("success", True)),
        "orchestrator_result": orchestrator_result,
        "peak_rss_mb": max(rss_before_mb, rss_after_mb),
        "rss_before_mb": rss_before_mb,
        "wall_sec": wall_sec,
    }


def _process_rss_mb() -> float:
    try:
        import os

        import psutil

        return float(psutil.Process(os.getpid()).memory_info().rss) / (
            1024.0 * 1024.0
        )
    except Exception:
        return 0.0


__all__ = [
    "DEFAULT_PROBE_SLICE_COUNT",
    "DEFAULT_PROBE_SAFETY_FACTOR",
    "SliceProbeResult",
    "SliceProbe",
]
