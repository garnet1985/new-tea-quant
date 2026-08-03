"""
Backtest Engine - Slice-based Probe

Head-phase sampling for slice_based:

- Full entity universe (never truncate entities).
- Slice width = resolved formal ``slice_open_days``.
- Sample the first ``probe_slice_count`` slices (default 2); those slices are
  real work and count toward official output.
- Remaining calendar continues in the same run; metrics refine ``preload_depth``.
"""
from __future__ import annotations

import copy
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.infra.machine_capacity.contracts import MachineCapacity

logger = logging.getLogger(__name__)

DEFAULT_PROBE_SLICE_COUNT: int = 2
DEFAULT_PROBE_SAFETY_FACTOR: float = 1.25


@dataclass(frozen=True)
class SliceProbeResult:
    """Per-slice unit costs from head-phase samples."""

    mb_per_slice_reader: float
    mb_per_slice_compute: float
    mb_per_slice_payload: float
    sec_per_slice_reader: float
    sec_per_slice_compute: float
    sec_per_slice_serialize: float = 0.0
    sec_per_slice_deserialize: float = 0.0
    slices_sampled: int = 0
    wall_sec: float = 0.0
    peak_rss_mb_reader: float = 0.0
    peak_rss_mb_compute: float = 0.0


class SliceProbe:
    """Head-phase helpers for slice_based planning."""

    @staticmethod
    def should_run(
        jobs: List[Dict[str, Any]],
        performance: Dict[str, Any],
    ) -> bool:
        if performance.get("dispatch_probe") is False:
            return False
        if performance.get("slice_probe") is False:
            return False
        # Skip when preload depth is already fixed (no need to sample for queue size).
        if performance.get("preload_depth") not in (None, "", "auto"):
            return False
        if not jobs:
            return False
        payload = BacktestJob.from_dict(jobs[0]).payload
        entity_ids = payload.get(BacktestJob.SLICE_BASED_ENTITY_KEY)
        if not isinstance(entity_ids, list) or not entity_ids:
            return False
        point_count = payload.get(BacktestJob.TIMELINE_POINT_COUNT_KEY)
        if not isinstance(point_count, int) or point_count <= 0:
            return False
        if not SliceProbe._has_worker_hooks(payload):
            return False
        return True

    @staticmethod
    def _has_worker_hooks(payload: Dict[str, Any]) -> bool:
        if payload.get("worker_module_path"):
            return True
        info = payload.get("strategy_info")
        if isinstance(info, dict) and info.get("hooks_module_path"):
            return True
        return False

    @staticmethod
    def head_slice_count(performance: Dict[str, Any]) -> int:
        return max(1, int(performance.get("probe_slice_count", DEFAULT_PROBE_SLICE_COUNT)))

    @staticmethod
    def annotate_payload_for_head_sampling(
        payload: Dict[str, Any],
        *,
        slice_open_days: int,
        probe_slice_count: int,
        sample_enabled: bool,
    ) -> Dict[str, Any]:
        """Mark payload so the executor samples the first N formal-width slices.

        Full entity universe and timeline_point_count are preserved; head slices are
        part of the official run (worker 从全局 calendar 解析 points，不读 payload.timeline).
        """
        out = dict(payload)
        out["_slice_head_sample_slices"] = (
            max(1, int(probe_slice_count)) if sample_enabled else 0
        )
        out["_slice_open_days"] = max(1, int(slice_open_days))
        out.pop("_slice_probe", None)
        out.pop("_dispatch_probe", None)
        return out

    @staticmethod
    def split_points_into_windows(
        points: List[str],
        *,
        slice_open_days: int,
    ) -> List[List[str]]:
        days = max(1, int(slice_open_days))
        windows: List[List[str]] = []
        for start in range(0, len(points), days):
            windows.append(list(points[start : start + days]))
        return windows

    @staticmethod
    def result_from_execute_report(
        report_or_result: Dict[str, Any],
        *,
        performance: Dict[str, Any],
        safety_factor: Optional[float] = None,
    ) -> SliceProbeResult:
        """Build ``SliceProbeResult`` from an execute return / JobReport data."""
        safety = max(
            1.0,
            float(
                safety_factor
                if safety_factor is not None
                else (
                    performance.get("slice_probe_safety_factor")
                    or performance.get("dispatch_probe_safety_factor")
                    or DEFAULT_PROBE_SAFETY_FACTOR
                )
            ),
        )
        body = report_or_result
        if "data" in body and isinstance(body.get("data"), dict):
            # JobReport-shaped
            if body.get("performance_metrics"):
                body = {
                    "success": body.get("success", True),
                    "performance_metrics": body.get("performance_metrics"),
                    "wall_sec": body.get("wall_sec"),
                }
            else:
                data = body["data"]
                body = dict(data)
                if "wall_sec" in report_or_result:
                    body.setdefault("wall_sec", report_or_result["wall_sec"])

        try:
            metrics = SliceProbe._extract_metrics_from_plan(body, safety_factor=safety)
        except RuntimeError:
            logger.warning("slice head samples missing; using plan defaults")
            return SliceProbe._default_result(performance)

        return SliceProbeResult(
            mb_per_slice_reader=float(metrics["mb_per_slice_reader"]),
            mb_per_slice_compute=float(metrics["mb_per_slice_compute"]),
            mb_per_slice_payload=float(metrics["mb_per_slice_payload"]),
            sec_per_slice_reader=float(metrics["sec_per_slice_reader"]),
            sec_per_slice_compute=float(metrics["sec_per_slice_compute"]),
            sec_per_slice_serialize=float(metrics.get("sec_per_slice_serialize") or 0.0),
            sec_per_slice_deserialize=float(
                metrics.get("sec_per_slice_deserialize") or 0.0
            ),
            slices_sampled=int(metrics["slices_sampled"]),
            wall_sec=float(body.get("wall_sec") or 0.0),
            peak_rss_mb_reader=float(metrics["peak_rss_mb_reader"]),
            peak_rss_mb_compute=float(metrics["peak_rss_mb_compute"]),
        )

    # --- legacy names kept as thin wrappers for older call sites / tests ---

    @staticmethod
    def build_probe_jobs(
        jobs: List[Dict[str, Any]],
        capacity: MachineCapacity,
        performance: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Deprecated throwaway path — prefer annotate + continuous execute."""
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
        """Build head-window payload: full entities, formal slice width × N.

        Kept for tests/helpers. Pipeline uses annotate_payload_for_head_sampling
        on the full calendar instead of this truncated calendar.
        """
        parsed = BacktestJob.from_dict(jobs[0])
        job_id, payload = parsed.id, parsed.payload
        probe = copy.deepcopy(payload)

        slice_days = max(
            1,
            int(
                performance.get("slice_open_days")
                if performance.get("slice_open_days") not in (None, "", "auto")
                else 20
            ),
        )
        probe_slice_count = SliceProbe.head_slice_count(performance)
        needed_open_days = probe_slice_count * slice_days
        original_count = probe.get(BacktestJob.TIMELINE_POINT_COUNT_KEY)
        if not isinstance(original_count, int) or original_count <= 0:
            raise ValueError(
                f"slice probe 需要正整数 {BacktestJob.TIMELINE_POINT_COUNT_KEY!r}"
            )
        probe[BacktestJob.TIMELINE_POINT_COUNT_KEY] = min(
            original_count, needed_open_days
        )

        entity_ids = probe.get(BacktestJob.SLICE_BASED_ENTITY_KEY)
        if not isinstance(entity_ids, list) or not entity_ids:
            raise ValueError(
                f"slice probe 需要非空 {BacktestJob.SLICE_BASED_ENTITY_KEY!r}"
            )
        entity_n = len(entity_ids)

        probe = SliceProbe.annotate_payload_for_head_sampling(
            probe,
            slice_open_days=slice_days,
            probe_slice_count=probe_slice_count,
            sample_enabled=True,
        )
        probe["_probe_job_id"] = f"{job_id}_probe"
        probe["slice_open_days"] = slice_days

        logger.info(
            "Slice head payload: job=%s slices=%s slice_days=%s entities=%s "
            "timeline_point_count=%s",
            job_id,
            probe_slice_count,
            slice_days,
            entity_n,
            probe[BacktestJob.TIMELINE_POINT_COUNT_KEY],
        )
        return probe

    @staticmethod
    def _extract_metrics_from_plan(
        orchestrator_result: Dict[str, Any],
        *,
        safety_factor: float,
    ) -> Dict[str, float]:
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
        serializes = [
            float(sample.get("serialize_sec") or 0.0)
            for sample in samples
            if float(sample.get("serialize_sec") or 0.0) > 0.0
        ]
        deserializes = [
            float(sample.get("deserialize_sec") or 0.0)
            for sample in samples
            if float(sample.get("deserialize_sec") or 0.0) > 0.0
        ]
        sec_reader = sum(loads) / len(loads) if loads else 0.1
        sec_compute = sum(computes) / len(computes) if computes else 0.1
        sec_serialize = sum(serializes) / len(serializes) if serializes else 0.0
        sec_deserialize = (
            sum(deserializes) / len(deserializes) if deserializes else 0.0
        )

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
            "sec_per_slice_serialize": sec_serialize,
            "sec_per_slice_deserialize": sec_deserialize,
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
        _ = performance
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


__all__ = [
    "DEFAULT_PROBE_SLICE_COUNT",
    "DEFAULT_PROBE_SAFETY_FACTOR",
    "SliceProbeResult",
    "SliceProbe",
]
