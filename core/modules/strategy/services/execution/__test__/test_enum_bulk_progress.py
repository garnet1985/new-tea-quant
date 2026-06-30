"""多股 dispatch job 进度与展开。"""
from core.modules.backtest_engine.contracts import JobReport, JobResult, JobStatus
from core.modules.strategy.services.execution.enum_job_pipeline import (
    count_progress_units_from_job_result,
    expand_bulk_job_results,
)


def test_count_progress_units_bulk():
    jr = JobResult(
        job_id="batch_0",
        status=JobStatus.COMPLETED,
        result={
            "bulk": True,
            "stock_results": [
                {"success": True, "stock_id": "000001.SZ"},
                {"success": False, "stock_id": "000002.SZ"},
            ],
        },
    )
    assert count_progress_units_from_job_result(jr) == (1, 1)


def test_expand_bulk_job_results():
    jr = JobResult(
        job_id="batch_0",
        status=JobStatus.COMPLETED,
        result={
            "bulk": True,
            "stock_results": [
                {"success": True, "stock_id": "000001.SZ", "opportunity_count": 3},
                {"success": True, "stock_id": "000002.SZ", "opportunity_count": 0},
            ],
        },
    )
    expanded = expand_bulk_job_results([jr])
    assert len(expanded) == 2
    assert expanded[0].job_id == "000001.SZ"
    assert expanded[0].result["opportunity_count"] == 3


def test_progress_units_from_report_bulk():
    from core.modules.strategy.services.execution.enum_job_pipeline import (
        _progress_units_from_execute_report,
    )

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
    assert _progress_units_from_execute_report(report) == (2, 2, 0)
