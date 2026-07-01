"""Price BacktestEngine timeline integration."""
from __future__ import annotations

from unittest.mock import patch

from core.modules.strategy.services.execution.price_job_pipeline import (
    run_price_factor_timeline_via_backtest_engine,
)


def test_run_price_factor_timeline_via_backtest_engine_calls_facade() -> None:
    stock_jobs = [
        {
            "stock_id": "000001.SZ",
            "strategy_name": "demo",
            "output_version_dir": "/tmp/out",
            "config": {"k": 1},
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
                "mode": "entity_based",
                "plan": None,
                "monitor_stats": None,
            },
        )()
        run_price_factor_timeline_via_backtest_engine(
            stock_jobs=stock_jobs,
            total_stocks=1,
        )
        run_mock.assert_called_once()
        args, kwargs = run_mock.call_args
        assert kwargs["performance"] is not None
        assert args[1].__name__ == "execute_price_factor_timeline_job"
        assert args[0][0]["id"] == "000001.SZ"
