"""Strategy enum calendar_slice integration with BacktestEngine.sliced."""
from __future__ import annotations

from unittest.mock import patch

from core.modules.backtest_engine.contracts import JobContext
from core.modules.strategy.services.execution.enum_job_pipeline import (
    execute_enumeration_sliced_job,
    run_enumeration_sliced_via_backtest_engine,
)


def test_execute_enumeration_sliced_job_preserves_auto_slice_open_days(monkeypatch) -> None:
    captured: dict = {}

    def fake_execute(context: JobContext) -> dict:
        captured["payload"] = context.payload
        return {"success": True}

    monkeypatch.setattr(
        "core.modules.strategy.services.execution.enum_job_pipeline.execute_enumeration_job",
        fake_execute,
    )
    monkeypatch.setattr(
        "core.modules.strategy.services.execution.worker_runtime.bootstrap_strategy_worker_data_manager",
        lambda: None,
    )
    monkeypatch.setattr(
        "core.modules.strategy.services.execution.worker_runtime.release_strategy_worker_runtime",
        lambda: None,
    )

    execute_enumeration_sliced_job(
        JobContext(
            job_id="calendar_slice",
            payload={
                "job_id": "calendar_slice",
                "enumeration_execution_mode": "calendar_slice",
                "slice_open_days": "auto",
                "strategy_name": "demo",
                "settings": {},
                "start_date": "20240101",
                "end_date": "20240131",
                "output_dir": "/tmp",
                "stock_ids": ["000001.SZ"],
                "worker_module_path": "m",
                "worker_class_name": "C",
                "_slice_plan": {"slice_open_days": 20},
                "_global_extra_cache": {},
            },
            task_name="enum:sliced",
        )
    )
    assert captured["payload"]["slice_open_days"] == "auto"
    assert captured["payload"]["enumeration_execution_mode"] == "calendar_slice"


def test_run_enumeration_sliced_via_backtest_engine_calls_facade() -> None:
    dispatch_jobs = [
        {
            "job_id": "calendar_slice",
            "enumeration_execution_mode": "calendar_slice",
            "strategy_name": "demo",
            "settings": {},
            "start_date": "20240101",
            "end_date": "20240131",
            "output_dir": "/tmp",
            "stock_ids": ["000001.SZ"],
            "backtest_calendar": {
                "open_dates": [f"202401{d:02d}" for d in range(1, 21)],
            },
        }
    ]
    with patch("core.modules.backtest_engine.BacktestEngine.slice_based.run") as run_mock:
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
                "mode": "slice_based",
                "plan": None,
                "monitor_stats": None,
            },
        )()
        run_enumeration_sliced_via_backtest_engine(
            dispatch_jobs=dispatch_jobs,
            global_extra_cache={},
            total_jobs=20,
        )
        run_mock.assert_called_once()
        kwargs = run_mock.call_args.kwargs
        assert kwargs["performance"] is not None
