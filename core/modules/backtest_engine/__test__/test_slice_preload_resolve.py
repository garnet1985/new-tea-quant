"""Unit tests for slice preload_depth sizing and performance resolve."""
from __future__ import annotations

from core.infra.machine_capacity import MachineCapacity
from core.modules.backtest_engine.core.performance.settings import SliceBasedPerformance
from core.modules.backtest_engine.core.schedule.slice_based.planner import SlicePlanner
from core.modules.backtest_engine.core.schedule.slice_based.preload import (
    ideal_preload_from_timings,
    resolve_preload_depth,
)
from core.modules.backtest_engine.core.schedule.slice_based.probe import SliceProbeResult


def test_ideal_preload_from_timings_ratio() -> None:
    # t_io=2, t_compute=1 → ceil(2*1.15)=3
    assert ideal_preload_from_timings(2.0, 1.0) == 3
    assert ideal_preload_from_timings(0.1, 0.1) == 2  # ceil(1.15)=2


def test_resolve_preload_clipped_by_memory() -> None:
    depth = resolve_preload_depth(
        t_io_sec=10.0,
        t_compute_sec=1.0,
        memory_budget_mb=200.0,
        mb_per_in_flight_slice=80.0,
    )
    # io wants ~12 but cap 8; mem: (200-128-64)/80 = 0 → clamped to 1
    assert depth == 1


def test_resolve_for_planning_fixes_readers_leaves_preload_auto() -> None:
    cap = MachineCapacity(
        cpu_count=8,
        memory_budget_mb=8192.0,
        memory_floor_mb=1024.0,
        reserve_cores=1,
    )
    resolved = SliceBasedPerformance.resolve_for_planning(
        {"reader_workers": "auto", "preload_depth": "auto", "queue_capacity": "auto"},
        cap,
        dispatch_slices=10,
    )
    assert resolved["reader_workers"] == 7  # 8-1
    assert resolved["preload_depth"] == "auto"


def test_resolve_for_planning_drops_deprecated_probe_truncation_knobs() -> None:
    cap = MachineCapacity(
        cpu_count=8,
        memory_budget_mb=8192.0,
        memory_floor_mb=1024.0,
        reserve_cores=1,
    )
    resolved = SliceBasedPerformance.resolve_for_planning(
        {
            "reader_workers": 2,
            "preload_depth": "auto",
            "probe_entity_count": 2,
            "probe_slice_open_days": 5,
            "probe_slice_count": 2,
        },
        cap,
        dispatch_slices=10,
    )
    assert "probe_entity_count" not in resolved
    assert "probe_slice_open_days" not in resolved
    assert resolved["probe_slice_count"] == 2


def test_refine_plan_from_probe_sets_ran_snapshot() -> None:
    cap = MachineCapacity(
        cpu_count=8,
        memory_budget_mb=8192.0,
        memory_floor_mb=1024.0,
        reserve_cores=1,
    )
    skeleton = SlicePlanner._resolve_slice_plan(
        [{"id": "j1", "payload": {"open_dates": [f"202401{d:02d}" for d in range(1, 31)], "entity_ids": ["a"]}}],
        cap,
        None,
        {
            "reader_workers": 7,
            "preload_depth": "auto",
            "queue_capacity": "auto",
            "slice_open_days": 20,
            "compute_processes": 1,
            "prefetch_enabled": True,
        },
        "test",
    )
    probe = SliceProbeResult(
        mb_per_slice_reader=20.0,
        mb_per_slice_compute=30.0,
        mb_per_slice_payload=10.0,
        sec_per_slice_reader=2.0,
        sec_per_slice_compute=1.0,
        slices_sampled=2,
        wall_sec=3.0,
    )
    refined = SlicePlanner.refine_plan_from_probe(
        skeleton,
        probe,
        cap,
        {"preload_depth": "auto", "prefetch_enabled": True},
    )
    assert refined.probe is not None
    assert refined.probe["ran"] is True
    assert refined.probe["slices_sampled"] == 2
    assert refined.probe["sec_per_slice_reader"] == 2.0
    assert refined.preload_depth == refined.queue_capacity


def test_base_plan_sets_queue_equal_preload_from_probe() -> None:
    cap = MachineCapacity(
        cpu_count=8,
        memory_budget_mb=8192.0,
        memory_floor_mb=1024.0,
        reserve_cores=1,
    )
    probe = SliceProbeResult(
        mb_per_slice_reader=20.0,
        mb_per_slice_compute=30.0,
        mb_per_slice_payload=10.0,
        sec_per_slice_reader=2.0,
        sec_per_slice_compute=1.0,
        sec_per_slice_serialize=0.05,
        sec_per_slice_deserialize=0.02,
        slices_sampled=2,
        wall_sec=1.0,
        peak_rss_mb_reader=40.0,
        peak_rss_mb_compute=50.0,
    )
    perf = {
        "reader_workers": 7,
        "preload_depth": "auto",
        "slice_open_days": 20,
        "compute_processes": 1,
        "prefetch_enabled": True,
    }
    jobs = [
        {
            "id": "j1",
            "payload": {
                "stock_ids": ["a"],
                "open_dates": [f"202401{d:02d}" for d in range(1, 21)],
            },
        }
    ]
    plan = SlicePlanner._resolve_base_plan(jobs, cap, probe, perf)
    assert plan.preload_depth == 3  # ceil(2/1*1.15)
    assert plan.queue_capacity == plan.preload_depth
    assert plan.reader_workers == 7


def test_oom_cuts_preload_not_readers() -> None:
    cap = MachineCapacity(
        cpu_count=8,
        memory_budget_mb=200.0,
        memory_floor_mb=64.0,
        reserve_cores=1,
    )
    probe = SliceProbeResult(
        mb_per_slice_reader=50.0,
        mb_per_slice_compute=40.0,
        mb_per_slice_payload=50.0,
        sec_per_slice_reader=2.0,
        sec_per_slice_compute=1.0,
        slices_sampled=1,
        wall_sec=1.0,
        peak_rss_mb_reader=50.0,
        peak_rss_mb_compute=40.0,
    )
    base = SlicePlanner._resolve_base_plan(
        [{"id": "j", "payload": {"stock_ids": ["a"], "open_dates": ["20240101"]}}],
        cap,
        probe,
        {
            "reader_workers": 7,
            "preload_depth": 8,
            "slice_open_days": 20,
            "compute_processes": 1,
        },
    )
    assert base.reader_workers == 7
    final = SlicePlanner._apply_oom_protection(base, cap, probe)
    assert final.reader_workers == 7
    assert final.preload_depth == final.queue_capacity
    assert final.preload_depth < 8
