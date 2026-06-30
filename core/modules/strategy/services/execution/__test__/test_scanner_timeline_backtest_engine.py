"""Strategy scanner timeline integration with BacktestEngine."""
from __future__ import annotations

from unittest.mock import patch

from core.modules.backtest_engine.contracts import JobContext
from core.modules.strategy.services.execution.scanner_job_pipeline import (
    execute_scanner_timeline_job,
    run_scanner_timeline_via_backtest_engine,
)


def test_execute_scanner_timeline_job_single_entity(monkeypatch) -> None:
    captured: dict = {}

    def fake_run(payload: dict) -> dict:
        captured["payload"] = payload
        return {"success": True, "stock_id": payload["stock_id"]}

    monkeypatch.setattr(
        "core.modules.strategy.services.execution.scanner_job_pipeline.run_scanner_worker_payload",
        fake_run,
    )
    monkeypatch.setattr(
        "core.modules.strategy.services.execution.worker_runtime.bootstrap_strategy_worker_data_manager",
        lambda: None,
    )
    monkeypatch.setattr(
        "core.modules.strategy.services.execution.worker_runtime.release_strategy_worker_runtime",
        lambda: None,
    )

    out = execute_scanner_timeline_job(
        JobContext(
            job_id="batch_0",
            payload={
                "jobs": [
                    {
                        "id": "000001.SZ",
                        "payload": {
                            "stock_id": "000001.SZ",
                            "strategy_name": "demo",
                            "execution_mode": "scan",
                            "settings": {},
                        },
                    }
                ]
            },
            task_name="scanner:test",
        )
    )
    assert out["success"] is True
    assert captured["payload"]["stock_id"] == "000001.SZ"


def test_run_scanner_timeline_via_backtest_engine_calls_facade() -> None:
    stock_jobs = [
        {
            "stock_id": "000001.SZ",
            "execution_mode": "scan",
            "strategy_name": "demo",
            "settings": {},
        }
    ]
    with patch("core.modules.backtest_engine.BacktestEngine.entity_based.run") as run_mock:
        run_mock.return_value = type(
            "RunResult",
            (),
            {
                "job_results": [],
                "success": True,
                "total_jobs": 0,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "elapsed_seconds": 0.0,
                "mode": "timeline",
                "plan": None,
                "monitor_stats": None,
            },
        )()
        run_scanner_timeline_via_backtest_engine(stock_jobs=stock_jobs, total_jobs=1)
        run_mock.assert_called_once()
        kwargs = run_mock.call_args.kwargs
        assert kwargs["performance"] is not None
        assert run_mock.call_args.args[0][0]["id"] == "000001.SZ"
