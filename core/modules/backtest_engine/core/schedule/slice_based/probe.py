"""
Backtest Engine - Slice-based Probe

1) Memory probe (SOT §2): load ``min_required`` open days × full entities → ``probe_mb``.
2) Head-phase timing samples during execute refine live queue depth N (SOT §5).
"""
from __future__ import annotations

import gc
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from core.modules.backtest_engine.core.shared.jobs import BacktestJob

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
    """Memory probe + head-phase helpers for slice_based planning."""

    @classmethod
    def needs_memory_probe(cls, performance: Dict[str, Any]) -> bool:
        """True when plan has neither ``probe_mb`` nor ``mb_per_open_day``."""
        if performance.get("probe_mb") not in (None, ""):
            return False
        if performance.get("mb_per_open_day") not in (None, ""):
            return False
        return True

    # RSS alone often under-counts (shared allocators / delayed commit). Prefer
    # payload walk; reject absurdly tiny probes that would inflate slice width.
    _MIN_PROBE_MB_PER_ENTITY = 0.02  # 20KB/entity for the probe window

    @classmethod
    def measure_probe_mb(
        cls,
        jobs: List[Dict[str, Any]],
        *,
        min_required: int,
        load_per_entity_window: Any = None,
    ) -> float:
        """Load W_probe open days for all entities; return ``probe_mb``.

        Uses ``max(RSS Δ, walked payload MB)``. Timings are logged only —
        never used for initial N (SOT §2).

        ``load_per_entity_window`` 由调用方注入（通常
        ``JobBundleLoader.load_per_entity_window``）。
        """
        if not jobs:
            raise ValueError("measure_probe_mb requires non-empty jobs")
        if load_per_entity_window is None:
            raise ValueError(
                "measure_probe_mb requires load_per_entity_window "
                "(via RunCallbacks.load_per_entity_window)"
            )
        payload = BacktestJob.from_dict(jobs[0]).payload
        start, end, width = cls._probe_window_bounds(payload, min_required=min_required)
        entity_n = cls._entity_count(payload)

        gc.collect()
        rss0 = cls._process_rss_mb()
        t0 = time.perf_counter()
        contracts = load_per_entity_window(
            payload,
            start=start,
            end=end,
            perf=None,
        )
        load_sec = max(0.0, time.perf_counter() - t0)
        rss1 = cls._process_rss_mb()
        rss_delta = max(float(rss1 - rss0), 0.0)
        payload_mb = cls.estimate_contracts_mb(contracts)
        probe_mb = max(rss_delta, payload_mb, 0.1)
        n_keys = len(contracts) if isinstance(contracts, dict) else 0
        del contracts
        gc.collect()

        logger.info(
            "slice memory probe: window=%s..%s width=%s entities=%s keys=%s "
            "probe_mb=%.2f (rss_delta=%.2f payload=%.2f) load_sec=%.3f "
            "(timing not used for initial N)",
            start,
            end,
            width,
            entity_n,
            n_keys,
            probe_mb,
            rss_delta,
            payload_mb,
            load_sec,
        )
        if n_keys <= 0:
            raise RuntimeError(
                f"slice memory probe loaded no contracts for window {start}..{end}"
            )
        # Warm process / allocator reuse can make RSS Δ ≈ 0 and walked size
        # collapse; use a conservative floor so width stays narrow instead of
        # failing the run (or worse, planning one giant slice).
        floor_mb = max(1, entity_n) * cls._MIN_PROBE_MB_PER_ENTITY
        if probe_mb < floor_mb:
            logger.warning(
                "slice memory probe below floor for entities=%s: "
                "probe_mb=%.2f < floor=%.2f (rss_delta=%.2f, payload=%.2f); "
                "using floor_mb as probe_mb (narrower slices)",
                entity_n,
                probe_mb,
                floor_mb,
                rss_delta,
                payload_mb,
            )
            return float(floor_mb)
        return probe_mb

    @classmethod
    def estimate_contracts_mb(cls, contracts: Any) -> float:
        """Best-effort deep size of contract payloads (MB)."""
        if not isinstance(contracts, dict) or not contracts:
            return 0.0
        total = 0
        for contract in contracts.values():
            data = getattr(contract, "data", contract)
            total += cls._nbytes(data)
        return float(total) / (1024.0 * 1024.0)

    @classmethod
    def _nbytes(cls, obj: Any, *, _seen: Optional[set] = None) -> int:
        if obj is None:
            return 0
        # Scalars: no identity de-dup (interned equal values would under-count rows).
        if isinstance(obj, (bytes, bytearray, memoryview)):
            return len(obj)
        if isinstance(obj, str):
            return len(obj) * 2
        if isinstance(obj, (int, float, bool)):
            return 24

        if _seen is None:
            _seen = set()
        oid = id(obj)
        if oid in _seen:
            return 0
        _seen.add(oid)

        nbytes = getattr(obj, "nbytes", None)
        if isinstance(nbytes, int):
            return max(0, nbytes)

        if isinstance(obj, dict):
            return sum(
                cls._nbytes(k, _seen=_seen) + cls._nbytes(v, _seen=_seen)
                for k, v in obj.items()
            )
        if isinstance(obj, list):
            if not obj:
                return 0
            # Homogeneous bar rows: n × first (avoids O(n) walk + shared-id collapse).
            if isinstance(obj[0], dict):
                return len(obj) * cls._nbytes(obj[0], _seen=set())
            return sum(cls._nbytes(x, _seen=_seen) for x in obj)
        if isinstance(obj, (tuple, set)):
            return sum(cls._nbytes(x, _seen=_seen) for x in obj)
        data = getattr(obj, "data", None)
        if data is not None and data is not obj:
            return cls._nbytes(data, _seen=_seen)
        try:
            import sys

            return int(sys.getsizeof(obj))
        except Exception:
            return 0

    @staticmethod
    def _entity_count(payload: Dict[str, Any]) -> int:
        specified = payload.get("entity_specified")
        if isinstance(specified, list) and specified:
            return len(specified)
        ids = payload.get("entity_ids")
        if isinstance(ids, list):
            return len([x for x in ids if str(x).strip()])
        return 0

    @classmethod
    def _probe_window_bounds(
        cls,
        payload: Dict[str, Any],
        *,
        min_required: int,
    ) -> Tuple[str, str, int]:
        from core.modules.backtest_engine.core.timeline.timeline import Timeline

        timeline = Timeline.read_for_job(payload)
        if timeline is None:
            raise RuntimeError(
                "slice memory probe 需要已发布的 Timeline（BacktestEngine.run 须先 stamp）"
            )
        points = list(timeline.clipped().points or [])
        if not points:
            raise RuntimeError("slice memory probe: timeline 无开市日")
        width = max(1, int(min_required))
        end_idx = min(width - 1, len(points) - 1)
        return str(points[0]), str(points[end_idx]), end_idx + 1

    @staticmethod
    def _process_rss_mb() -> float:
        try:
            import os

            import psutil

            return float(psutil.Process(os.getpid()).memory_info().rss) / (1024.0 * 1024.0)
        except Exception:
            return 0.0

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
