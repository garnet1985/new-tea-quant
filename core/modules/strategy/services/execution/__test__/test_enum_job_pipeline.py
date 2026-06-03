"""枚举 JobPipeline 辅助函数。"""
from core.infra.job_pipeline.types import JobReport, RunProgress
from core.infra.worker.multi_process.process_worker import JobStatus
from core.modules.strategy.services.execution.enum_job_pipeline import (
    job_report_to_job_result,
    legacy_progress_from_counts,
    legacy_progress_from_run_progress,
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


def test_legacy_progress_from_run_progress():
    payload = legacy_progress_from_run_progress(
        RunProgress(finished=10, total=100, ok=9, fail=1),
        total_jobs=100,
        finished_offset=40,
        last_job_id="000001.SZ",
        last_job_status="completed",
    )
    assert payload["progress_pct"] == 50


def test_legacy_progress_from_counts():
    payload = legacy_progress_from_counts(
        total_jobs=100,
        finished=50,
        completed_jobs=48,
        failed_jobs=2,
    )
    assert payload["progress_pct"] == 50
    assert payload["total_jobs"] == 100
    assert payload["completed_jobs"] == 48
    assert payload["failed_jobs"] == 2
