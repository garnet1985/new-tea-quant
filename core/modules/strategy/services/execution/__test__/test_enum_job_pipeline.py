"""BacktestEngine 执行辅助函数。"""
from core.modules.backtest_engine.core.shared.types import JobReport, JobStatus
from core.modules.strategy.services.execution.stock_job_pipeline import (
    job_progress_payload,
    job_report_to_job_result,
)


def test_job_report_to_job_result_completed():
    report = JobReport(job_id="000001.SZ", success=True, data={"success": True, "stock_id": "000001.SZ"})
    jr = job_report_to_job_result(report)
    assert jr.status == JobStatus.COMPLETED
    assert jr.result == report.data


def test_job_report_to_job_result_failed():
    report = JobReport(
        job_id="000002.SZ",
        success=False,
        data={"success": False},
        error="boom",
    )
    jr = job_report_to_job_result(report)
    assert jr.status == JobStatus.FAILED
    assert jr.error == "boom"


def test_job_report_to_job_result_bulk_partial_failure():
    report = JobReport(
        job_id="price_batch",
        success=False,
        data={
            "success": False,
            "bulk": True,
            "stock_results": [
                {"success": True, "stock_id": "000001.SZ"},
                {"success": False, "stock_id": "000002.SZ", "error": "boom"},
            ],
        },
        error="partial",
    )
    jr = job_report_to_job_result(report)
    assert jr.status == JobStatus.COMPLETED
    assert jr.result is report.data


def test_job_progress_payload():
    payload = job_progress_payload(
        total_jobs=100,
        finished=50,
        completed_jobs=48,
        failed_jobs=2,
    )
    assert payload["progress_pct"] == 50
    assert payload["total_jobs"] == 100
    assert payload["completed_jobs"] == 48
    assert payload["failed_jobs"] == 2
