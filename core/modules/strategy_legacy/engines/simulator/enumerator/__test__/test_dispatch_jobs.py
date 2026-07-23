"""dispatch job 分组。"""
from core.modules.strategy.engines.simulator.enumerator.stock_based.dispatch_jobs import (
    build_dispatch_jobs,
    chunk_stock_ids,
    count_stocks_in_dispatch_jobs,
    dispatch_job_id,
)


def test_chunk_stock_ids():
    assert chunk_stock_ids(["a", "b", "c", "d", "e"], 2) == [["a", "b"], ["c", "d"], ["e"]]
    assert chunk_stock_ids(["x"], 10) == [["x"]]


def test_build_dispatch_jobs_entities_per_job():
    jobs = build_dispatch_jobs(
        strategy_name="example",
        settings_payload={"name": "t"},
        output_dir="/tmp/out",
        worker_ref={"worker_module_path": "m", "worker_class_name": "W"},
        stock_ids=["000001.SZ", "000002.SZ", "600519.SH"],
        start_date="20230101",
        end_date="20251231",
        entities_per_job=2,
    )
    assert len(jobs) == 2
    assert jobs[0]["stock_ids"] == ["000001.SZ", "000002.SZ"]
    assert jobs[0]["job_id"] == dispatch_job_id(0, jobs[0]["stock_ids"])
    assert count_stocks_in_dispatch_jobs(jobs) == 3


def test_build_dispatch_jobs_single_stock_has_stock_id():
    jobs = build_dispatch_jobs(
        strategy_name="example",
        settings_payload={},
        output_dir="/tmp",
        worker_ref={"worker_module_path": "m", "worker_class_name": "W"},
        stock_ids=["600519.SH"],
        start_date="20230101",
        end_date="20251231",
        entities_per_job=1,
    )
    assert jobs[0]["stock_id"] == "600519.SH"
    assert jobs[0]["job_id"] == "600519.SH"
