#!/usr/bin/env python3
"""扫描 JobPipeline 辅助函数。"""

from core.modules.strategy.services.execution.scanner_job_pipeline import (
    build_scanner_payload,
    resolve_scanner_max_workers,
)

def test_build_scanner_payload_passthrough():
    job = {
        "stock_id": "000001.SZ",
        "execution_mode": "scan",
        "strategy_name": "demo",
        "settings": {},
        "scan_date": "20260102",
        "worker_module_path": "userspace.strategies.demo.strategy_worker",
        "worker_class_name": "StrategyWorker",
    }
    assert build_scanner_payload(job) == job


def test_resolve_scanner_max_workers_auto():
    assert resolve_scanner_max_workers("auto") >= 1
