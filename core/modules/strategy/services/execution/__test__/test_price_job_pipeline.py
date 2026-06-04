"""价格 JobPipeline 辅助函数。"""
from core.infra.job_pipeline.types import JobReport
from core.infra.worker.multi_process.process_worker import JobStatus
from core.modules.strategy.services.execution.price_job_pipeline import (
    build_price_factor_payload,
    workbench_disk_progress,
)
from core.modules.strategy.services.execution.stock_job_pipeline import job_report_to_job_result


def test_build_price_factor_payload_batch():
    job = {
        "job_id": "price_0",
        "stock_ids": ["000001.SZ", "000002.SZ"],
        "stock_jobs": [
            {
                "stock_id": "000001.SZ",
                "strategy_name": "demo",
                "opportunities_path": "/tmp/o1.csv",
                "targets_path": "/tmp/t1.csv",
                "output_version_dir": "/tmp/out",
                "config": {"k": 1},
            },
            {
                "stock_id": "000002.SZ",
                "strategy_name": "demo",
                "opportunities_path": "/tmp/o2.csv",
                "targets_path": "/tmp/t2.csv",
                "output_version_dir": "/tmp/out",
                "config": {"k": 1},
            },
        ],
    }
    payload = build_price_factor_payload(job)
    assert payload["job_id"] == "price_0"
    assert len(payload["stock_jobs"]) == 2
    assert payload["stock_ids"] == ["000001.SZ", "000002.SZ"]


def test_job_report_to_job_result_price_success():
    report = JobReport(
        job_id="000001.SZ",
        success=True,
        data={"success": True, "stock_id": "000001.SZ"},
    )
    jr = job_report_to_job_result(report)
    assert jr.status == JobStatus.COMPLETED
    assert jr.result["stock_id"] == "000001.SZ"


def test_workbench_disk_progress_mapping():
    seen: list[float] = []

    def cb(v: float) -> None:
        seen.append(v)

    workbench_disk_progress({"progress_pct": 50}, cb)
    assert len(seen) == 1
    assert 50.0 < seen[0] < 52.0
