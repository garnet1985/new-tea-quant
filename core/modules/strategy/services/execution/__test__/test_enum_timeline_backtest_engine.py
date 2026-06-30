"""Strategy enum timeline integration with BacktestEngine (black-box run)."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from core.modules.backtest_engine.contracts import JobContext
from core.modules.strategy.services.execution.enum_job_pipeline import (
    _merge_enumeration_batch,
    execute_enumeration_timeline_job,
    run_enumeration_timeline_via_backtest_engine,
)


def test_merge_enumeration_batch_combines_engine_jobs() -> None:
    merged = _merge_enumeration_batch(
        [
            {
                "id": "000001.SZ",
                "payload": {
                    "stock_id": "000001.SZ",
                    "strategy_name": "demo",
                    "settings": {},
                },
            },
            {
                "id": "000002.SZ",
                "payload": {
                    "stock_id": "000002.SZ",
                    "strategy_name": "demo",
                    "settings": {},
                },
            },
        ],
        "batch_job",
    )
    assert merged["stock_ids"] == ["000001.SZ", "000002.SZ"]
    assert merged["strategy_name"] == "demo"
    assert "000001.SZ" in merged["job_id"]


def test_merge_enumeration_batch_rejects_flat_rows() -> None:
    with pytest.raises(ValueError, match="BacktestEngine job"):
        _merge_enumeration_batch(
            [{"stock_id": "000001.SZ", "strategy_name": "demo", "settings": {}}],
            "batch_job",
        )


def test_execute_enumeration_timeline_job_delegates_to_worker(monkeypatch) -> None:
    captured: dict = {}

    def fake_execute(context: JobContext) -> dict:
        captured["payload"] = context.payload
        return {"success": True}

    monkeypatch.setattr(
        "core.modules.strategy.services.execution.enum_job_pipeline.execute_enumeration_job",
        fake_execute,
    )

    execute_enumeration_timeline_job(
        JobContext(
            job_id="batch_0",
            payload={
                "jobs": [
                    {
                        "id": "000001.SZ",
                        "payload": {
                            "stock_id": "000001.SZ",
                            "strategy_name": "demo",
                            "settings": {"a": 1},
                            "start_date": "20240101",
                            "end_date": "20240131",
                            "output_dir": "/tmp",
                            "worker_module_path": "m",
                            "worker_class_name": "C",
                        },
                    }
                ],
                "_global_extra_cache": {"k": []},
            },
            task_name="enum:test",
        )
    )
    assert captured["payload"]["stock_ids"] == ["000001.SZ"]
    assert captured["payload"]["strategy_name"] == "demo"


def test_run_enumeration_timeline_via_backtest_engine_calls_facade() -> None:
    entity_jobs = [
        {
            "stock_id": "000001.SZ",
            "strategy_name": "demo",
            "settings": {},
            "start_date": "20240101",
            "end_date": "20240131",
            "output_dir": "/tmp",
            "worker_module_path": "m",
            "worker_class_name": "C",
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
        run_enumeration_timeline_via_backtest_engine(
            entity_jobs=entity_jobs,
            global_extra_cache={},
            total_jobs=1,
        )
        run_mock.assert_called_once()
        args, kwargs = run_mock.call_args
        assert kwargs["performance"] is not None
        assert kwargs["task_name"] == "enum"
        assert args[1].__name__ == "execute_enumeration_timeline_job"
        assert args[0][0] == {
            "id": "000001.SZ",
            "payload": {
                **entity_jobs[0],
                "_global_extra_cache": {},
            },
        }
