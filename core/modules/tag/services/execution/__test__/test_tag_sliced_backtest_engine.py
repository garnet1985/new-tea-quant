"""Tag calendar_slice integration with BacktestEngine.sliced + staged save."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.modules.backtest_engine.contracts import JobContext
from core.modules.tag.services.execution.tag_job_pipeline import (
    TAG_SLICED_EXECUTOR_KEY,
    execute_tag_sliced_job,
    run_tag_sliced_via_backtest_engine,
    _slice_save_hook,
)


def test_execute_tag_sliced_job_wires_slice_save_hook(monkeypatch) -> None:
    captured: dict = {}

    def fake_run(payload, on_slice_tag_values=None):
        captured["payload"] = payload
        captured["hook"] = on_slice_tag_values
        return {
            "success": True,
            "bulk": True,
            "tag_values": [],
            "total_tags": 0,
            "entity_count": 1,
            "errors": [],
        }

    monkeypatch.setattr(
        "core.modules.tag.engines.sliced.worker.run_tag_calendar_slice_payload",
        fake_run,
    )

    rows: list = []

    def hook(batch):
        rows.extend(batch)

    token = _slice_save_hook.set(hook)
    try:
        execute_tag_sliced_job(
            JobContext(
                job_id="scenario_calendar_slice",
                payload={
                    "job_id": "scenario_calendar_slice",
                    "entity_ids": ["000001"],
                    "tag_execution_mode": "calendar_slice",
                    "slice_open_days": "auto",
                    "_executor": "tag",
                    "_slice_plan": {"slice_open_days": 20},
                },
                run_name="tag:demo",
            )
        )
    finally:
        _slice_save_hook.reset(token)

    assert captured["payload"]["entity_ids"] == ["000001"]
    assert captured["hook"] is hook
    assert "slice_open_days" in captured["payload"]


def test_run_tag_sliced_via_backtest_engine_staged_save(monkeypatch) -> None:
    save_batches: list[list] = []

    def fake_run(payload, on_slice_tag_values=None):
        if on_slice_tag_values is not None:
            on_slice_tag_values([{"entity_id": "000001", "as_of_date": "20240102"}])
            on_slice_tag_values([{"entity_id": "000001", "as_of_date": "20240103"}])
        return {
            "success": True,
            "bulk": True,
            "tag_values": [],
            "total_tags": 2,
            "entity_count": 1,
            "errors": [],
        }

    monkeypatch.setattr(
        "core.modules.tag.engines.sliced.worker.run_tag_calendar_slice_payload",
        fake_run,
    )

    def fake_save_fn(rows):
        save_batches.append(list(rows))
        return len(rows)

    monkeypatch.setattr(
        "core.modules.tag.services.execution.tag_job_pipeline._make_tag_save_fn",
        lambda _name: fake_save_fn,
    )

    def fake_be_run(jobs, execute_fn, **kwargs):
        execute_fn(
            JobContext(
                job_id=jobs[0]["id"],
                payload=jobs[0]["payload"],
                run_name=kwargs["run_name"],
            )
        )
        return type(
            "RunResult",
            (),
            {
                "job_results": [],
                "success": True,
                "total_jobs": 1,
                "completed_jobs": 1,
                "failed_jobs": 0,
                "elapsed_seconds": 0.0,
                "mode": "sliced",
                "plan": None,
                "monitor_stats": None,
            },
        )()

    with patch(
        "core.modules.backtest_engine.BacktestEngine.sliced.run",
        side_effect=fake_be_run,
    ) as run_mock:
        result = run_tag_sliced_via_backtest_engine(
            dispatch_jobs=[
                {
                    "job_id": "scenario_calendar_slice",
                    "entity_ids": ["000001"],
                    "tag_execution_mode": "calendar_slice",
                    "slice_open_days": "auto",
                }
            ],
            settings={
                "scenario_name": "demo",
                "performance": {"save_batch_size": 1, "dry_run": False},
            },
            run_name="tag:demo",
        )

    run_mock.assert_called_once()
    assert run_mock.call_args.kwargs["executor_key"] == TAG_SLICED_EXECUTOR_KEY
    assert result["saved_tag_values"] == 2
    assert len(save_batches) == 2
    assert save_batches[0][0]["as_of_date"] == "20240102"
    assert save_batches[1][0]["as_of_date"] == "20240103"


def test_run_tag_sliced_via_backtest_engine_calls_facade() -> None:
    with patch("core.modules.backtest_engine.BacktestEngine.sliced.run") as run_mock:
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
                "mode": "sliced",
                "plan": None,
                "monitor_stats": None,
            },
        )()
        run_tag_sliced_via_backtest_engine(
            dispatch_jobs=[{"job_id": "x", "entity_ids": ["000001"]}],
            settings={"scenario_name": "demo", "performance": {}},
        )
        run_mock.assert_called_once()
