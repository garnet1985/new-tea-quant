"""Unit tests for slice preload_depth sizing and performance resolve."""
from __future__ import annotations

from core.infra.machine_capacity.contracts import MachineCapacity
from core.modules.backtest_engine.core.performance.settings import SliceBasedPerformance
from core.modules.backtest_engine.core.schedule.slice_based.planner import SlicePlanner
from core.modules.backtest_engine.core.schedule.slice_based.probe import SliceProbeResult
from core.modules.backtest_engine.core.schedule.slice_based.slice_width import (
    SliceMemoryPlanner,
)


def test_refine_queue_clipped_by_memory() -> None:
    depth = SliceMemoryPlanner.refine_queue_depth(
        budget_mb=200.0,
        mb_per_slice=80.0,
        reader_workers=1,
        current_queue=4,
        t_load_sec=2.0,
        t_compute_sec=1.0,
    )
    # n_max = floor(160/80 - 2 - 1) = floor(2-3) = 0
    assert depth == 0


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
    # R = max(0, 8 - 1 - 1) = 6
    assert resolved["reader_workers"] == 6
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
            "reader_workers": 6,
            "preload_depth": 4,
            "queue_capacity": 4,
            "slice_open_days": 20,
            "compute_processes": 1,
            "prefetch_enabled": True,
        },
        "test",
    )
    assert skeleton.preload_depth == 4
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
    # n_ideal = ceil(2/1) = 2; memory ample → 2
    assert refined.preload_depth == 2


def test_base_plan_uses_resolved_preload_depth() -> None:
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
        "reader_workers": 6,
        "preload_depth": 6,
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
    assert plan.preload_depth == 6
    assert plan.queue_capacity == plan.preload_depth
    assert plan.reader_workers == 6


def test_resolve_memory_plan_sets_width_queue_and_readers() -> None:
    cap = MachineCapacity(
        cpu_count=8,
        memory_budget_mb=8192.0,
        memory_floor_mb=1024.0,
        reserve_cores=1,
    )
    mem = SlicePlanner._resolve_memory_plan(
        cap,
        {
            "mb_per_open_day": 1.0,
            "min_required_records": 20,
        },
        is_auto_width=True,
        explicit_width=None,
    )
    assert mem.reader_workers == 6
    assert mem.slice_open_days >= 20
    assert mem.queue_depth >= 0
    assert mem.peak_slices == 2 + mem.queue_depth + mem.reader_workers

    plan = SlicePlanner._resolve_slice_plan(
        [
            {
                "id": "j1",
                "payload": {
                    "entity_ids": ["a"],
                    "timeline_point_count": 200,
                },
            }
        ],
        cap,
        None,
        {
            "reader_workers": mem.reader_workers,
            "preload_depth": mem.queue_depth,
            "slice_open_days": mem.slice_open_days,
            "compute_processes": 1,
            "prefetch_enabled": True,
        },
        "test",
    )
    assert plan.reader_workers == mem.reader_workers
    assert plan.slice_open_days == mem.slice_open_days
    assert plan.preload_depth == mem.queue_depth
