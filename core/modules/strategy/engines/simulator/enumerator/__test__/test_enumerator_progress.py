"""Enumerator progress plan: entity_timeline vs calendar_slice."""
from core.modules.strategy.engines.simulator.enumerator.shared.progress_axis import (
    enumeration_progress_metadata,
)
from core.modules.strategy.engines.simulator.enumerator.stock_based.progress import (
    ENTITY_PROGRESS_MODE_BUNDLE,
    ENTITY_PROGRESS_MODE_STOCK,
    PROGRESS_AXIS_ENTITY_BUNDLE,
    PROGRESS_AXIS_ENTITY_STOCK,
    entity_progress_units_from_execute_report,
    resolve_entity_progress_plan,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.progress import (
    resolve_calendar_progress_plan,
)
from core.infra.job_pipeline.types import JobReport


def _sample_jobs(n_stocks: int, n_jobs: int):
    jobs = []
    per = max(1, n_stocks // n_jobs)
    for i in range(n_jobs):
        ids = [f"{j:06d}.SZ" for j in range(i * per, min(n_stocks, (i + 1) * per))]
        jobs.append({"stock_ids": ids})
    return jobs


def test_entity_progress_stock_mode():
    jobs = _sample_jobs(10, 2)
    plan = resolve_entity_progress_plan(jobs, progress_mode="stock")
    assert plan["entity_progress_mode"] == ENTITY_PROGRESS_MODE_STOCK
    assert plan["entity_progress_total"] == 10
    assert plan["progress_axis"] == PROGRESS_AXIS_ENTITY_STOCK


def test_entity_progress_bundle_mode():
    jobs = _sample_jobs(10, 2)
    plan = resolve_entity_progress_plan(jobs, progress_mode="bundle")
    assert plan["entity_progress_mode"] == ENTITY_PROGRESS_MODE_BUNDLE
    assert plan["entity_progress_total"] == 2
    assert plan["progress_axis"] == PROGRESS_AXIS_ENTITY_BUNDLE


def test_entity_progress_units_bundle():
    report = JobReport(job_id="batch_0", success=True, data={"bulk": True, "stock_results": [{}, {}]})
    finished, ok, fail = entity_progress_units_from_execute_report(
        report, progress_mode=ENTITY_PROGRESS_MODE_BUNDLE
    )
    assert (finished, ok, fail) == (1, 1, 0)


def test_entity_progress_units_stock():
    report = JobReport(
        job_id="batch_0",
        success=True,
        data={
            "bulk": True,
            "stock_results": [
                {"success": True, "stock_id": "a"},
                {"success": True, "stock_id": "b"},
            ],
        },
    )
    finished, ok, fail = entity_progress_units_from_execute_report(
        report, progress_mode=ENTITY_PROGRESS_MODE_STOCK
    )
    assert (finished, ok, fail) == (2, 2, 0)


def test_enumeration_progress_metadata_calendar_open_date():
    jobs = [
        {
            "enumeration_execution_mode": "calendar_slice",
            "calendar_progress_mode": "open_date",
        }
    ]
    meta = enumeration_progress_metadata(jobs)
    assert meta["progress_axis"] == "calendar_open_date"


def test_calendar_progress_slice_mode():
    open_dates = [f"2024-01-{d:02d}" for d in range(1, 11)]
    plan = resolve_calendar_progress_plan(
        open_dates=open_dates,
        slice_open_days=5,
        progress_mode="slice",
    )
    assert plan["calendar_progress_total"] == 2
    assert plan["calendar_open_date_count"] == 10


def test_calendar_progress_open_date_mode():
    open_dates = [f"2024-01-{d:02d}" for d in range(1, 6)]
    plan = resolve_calendar_progress_plan(
        open_dates=open_dates,
        slice_open_days=5,
        progress_mode="open_date",
    )
    assert plan["calendar_progress_total"] == 5
