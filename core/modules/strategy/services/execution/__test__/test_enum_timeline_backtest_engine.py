"""Strategy enum timeline integration with BacktestEngine (black-box run)."""
from __future__ import annotations

from unittest.mock import patch

from core.infra.job_pipeline import JobContext
from core.modules.strategy.services.execution.enum_job_pipeline import (
    _merge_enumeration_batch,
    execute_enumeration_timeline_job,
    run_enumeration_timeline_via_backtest_engine,
)


def test_merge_enumeration_batch_combines_entities() -> None:
    merged = _merge_enumeration_batch(
        [
            {"stock_id": "000001.SZ", "strategy_name": "demo", "settings": {}},
            {"stock_id": "000002.SZ", "strategy_name": "demo", "settings": {}},
        ],
        "batch_job",
    )
    assert merged["stock_ids"] == ["000001.SZ", "000002.SZ"]
    assert merged["strategy_name"] == "demo"
    assert "000001.SZ" in merged["job_id"]


def test_merge_enumeration_batch_unwraps_backtest_engine_jobs() -> None:
    merged = _merge_enumeration_batch(
        [
            {
                "id": "000001.SZ",
                "payload": {
                    "stock_id": "000001.SZ",
                    "entity_id": "000001.SZ",
                    "strategy_name": "demo",
                    "settings": {},
                },
            },
            {
                "id": "000002.SZ",
                "payload": {
                    "stock_id": "000002.SZ",
                    "entity_id": "000002.SZ",
                    "strategy_name": "demo",
                    "settings": {},
                },
            },
        ],
        "batch_job",
    )
    assert merged["stock_ids"] == ["000001.SZ", "000002.SZ"]
    assert merged["strategy_name"] == "demo"


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
                        "stock_id": "000001.SZ",
                        "strategy_name": "demo",
                        "settings": {"a": 1},
                        "start_date": "20240101",
                        "end_date": "20240131",
                        "output_dir": "/tmp",
                        "worker_module_path": "m",
                        "worker_class_name": "C",
                    }
                ],
                "_global_extra_cache": {"k": []},
            },
            run_name="enum:test",
        )
    )
    assert captured["payload"]["stock_ids"] == ["000001.SZ"]
    assert captured["payload"]["strategy_name"] == "demo"


def test_run_enumeration_timeline_via_backtest_engine_calls_facade() -> None:
    entity_jobs = [
        {
            "job_id": "000001.SZ",
            "stock_id": "000001.SZ",
            "entity_id": "000001.SZ",
            "strategy_name": "demo",
            "settings": {},
            "start_date": "20240101",
            "end_date": "20240131",
            "output_dir": "/tmp",
            "worker_module_path": "m",
            "worker_class_name": "C",
        }
    ]
    with patch("core.modules.backtest_engine.BacktestEngine.timeline.run") as run_mock:
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
        run_enumeration_timeline_via_backtest_engine(
            entity_jobs=entity_jobs,
            global_extra_cache={},
            total_jobs=1,
        )
        run_mock.assert_called_once()
        args, kwargs = run_mock.call_args
        assert kwargs["executor_key"] == "strategy.enum"
        assert args[1].__name__ == "execute_enumeration_timeline_job"
