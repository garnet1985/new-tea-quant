"""Unit tests for slice preload_depth sizing and performance resolve."""
from __future__ import annotations

from core.infra.machine_capacity.contracts import MachineCapacity
from core.modules.backtest_engine.core.performance.settings import SliceBasedPerformance
from core.modules.backtest_engine.core.schedule.slice_based.planner import SlicePlanner
from core.modules.backtest_engine.core.schedule.slice_based.probe import SliceProbeResult
from core.modules.backtest_engine.core.schedule.slice_based.slice_width import (
    DEFAULT_PRELOAD_DEPTH,
    MAX_PRELOAD_DEPTH,
    resolve_reader_queue_depth,
)


def test_resolve_reader_queue_clipped_by_memory() -> None:
    depth = resolve_reader_queue_depth(
        available_mb=200.0,
        mb_per_slice=80.0,
        compute_processes=1,
        current_depth=None,
        max_depth=MAX_PRELOAD_DEPTH,
    )
    # usable ≈ 200*0.85 - 80 = 90 → floor(90/80)=1
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


def test_refine_plan_from_probe_sets_ran_snapshot() -> None:
    cap = MachineCapacity(
        cpu_count=8,
        memory_budget_mb=8192.0,
        memory_floor_mb=1024.0,
        reserve_cores=1,
    )
    skeleton = SlicePlanner._resolve_slice_plan(
        [{"id": "j1", "payload": {"timeline_point_count": 30, "entity_ids": ["a"]}}],
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
    assert skeleton.preload_depth == DEFAULT_PRELOAD_DEPTH
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
    # Memory-ample → queue sized up toward MAX from provisional DEFAULT.
    assert refined.preload_depth >= DEFAULT_PRELOAD_DEPTH


def test_base_plan_sets_queue_from_memory_not_timing() -> None:
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
                "entity_ids": ["a"],
                "timeline_point_count": 20,
            },
        }
    ]
    plan = SlicePlanner._resolve_base_plan(jobs, cap, probe, perf)
    # Old timing path wanted ceil(2/1*1.15)=3; new path is memory-only → MAX.
    assert plan.preload_depth == MAX_PRELOAD_DEPTH
    assert plan.queue_capacity == plan.preload_depth
    assert plan.reader_workers == 7


def test_tight_memory_keeps_readers_and_small_queue() -> None:
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
        [{"id": "j", "payload": {"entity_ids": ["a"], "timeline_point_count": 1}}],
        cap,
        probe,
        {
            "reader_workers": 7,
            "preload_depth": "auto",
            "slice_open_days": 20,
            "compute_processes": 1,
            "prefetch_enabled": True,
        },
    )
    final = SlicePlanner._attach_memory_budgets(base, probe)
    assert final.reader_workers == 7
    assert final.preload_depth == final.queue_capacity
    assert final.preload_depth == 1
