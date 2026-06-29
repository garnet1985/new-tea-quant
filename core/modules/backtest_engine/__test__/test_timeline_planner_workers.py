"""Timeline planner worker concurrency (memory budget must not double-subtract floor)."""
from __future__ import annotations

from core.modules.backtest_engine.core.shared.machine_info import MachineCapacity
from core.modules.backtest_engine.core.timeline_based.planner import TimelinePlanner


def test_resolve_max_workers_auto_uses_cpu_cap() -> None:
    performance = {
        "max_workers": "auto",
        "prefetch_ahead": 1,
        "reserve_cores": 2,
    }

    workers, source = TimelinePlanner._resolve_max_workers(
        total_entities=473,
        entities_per_job=5,
        worker_job_budget_mb=19.0,
        available_memory_mb=3500.0,
        performance=performance,
        log_label="enum",
    )

    assert workers == 8
    assert source == "auto"


def test_resolve_max_workers_respects_max_parallel_jobs_cap() -> None:
    performance = {
        "max_workers": "auto",
        "prefetch_ahead": 1,
        "reserve_cores": 2,
        "max_parallel_jobs_cap": 5,
    }

    workers, source = TimelinePlanner._resolve_max_workers(
        total_entities=473,
        entities_per_job=5,
        worker_job_budget_mb=19.0,
        available_memory_mb=3500.0,
        performance=performance,
        log_label="enum",
    )

    assert workers == 5
    assert source == "auto"


def test_resolve_max_workers_capped_by_dispatch_jobs() -> None:
    performance = {
        "max_workers": "auto",
        "prefetch_ahead": 1,
        "reserve_cores": 2,
    }

    workers, source = TimelinePlanner._resolve_max_workers(
        total_entities=8,
        entities_per_job=5,
        worker_job_budget_mb=19.0,
        available_memory_mb=3500.0,
        performance=performance,
        log_label="enum",
    )

    assert workers == 2
    assert source == "auto"


def test_resolve_max_workers_memory_capped_on_tiny_budget() -> None:
    performance = {"max_workers": "auto", "prefetch_ahead": 1, "reserve_cores": 1}

    workers, source = TimelinePlanner._resolve_max_workers(
        total_entities=473,
        entities_per_job=5,
        worker_job_budget_mb=100.0,
        available_memory_mb=350.0,
        performance=performance,
        log_label="enum",
    )

    assert workers == 2
    assert source == "memory_capped"


def test_resolve_entities_per_job_auto_defaults_to_five() -> None:
    performance = {"entities_per_job_min": 1, "entities_per_job_max": 50}

    epj, source = TimelinePlanner._resolve_entities_per_job(
        total_entities=473,
        mb_per_entity=3.9,
        memory_budget_mb=3500.0,
        performance=performance,
        log_label="enum",
    )

    assert epj == 5
    assert source == "default"
