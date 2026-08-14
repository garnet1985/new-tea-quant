"""Tests for workbench run launcher (V2-05 / V2-06)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.bff.APIs.strategy.routes.runner.workbench_run import WorkbenchRunLauncher
from core.modules.strategy.core.services.progress import (
    PipelineProgress,
    ProgressRecorder,
)


def test_normalize_step():
    assert WorkbenchRunLauncher.normalize_step("enum") == "enum"
    assert WorkbenchRunLauncher.normalize_step("PRICE") == "price"
    assert WorkbenchRunLauncher.normalize_step("portfolio") == "portfolio"
    assert WorkbenchRunLauncher.normalize_step("capital") is None
    assert WorkbenchRunLauncher.normalize_step("nope") is None


def test_pipeline_progress_roundtrip_via_launcher(tmp_path, monkeypatch):
    def _build(channel, file_key):
        return tmp_path / "progress" / channel / f"{file_key}.json"

    monkeypatch.setattr(ProgressRecorder, "build_path", staticmethod(_build))

    PipelineProgress.seed("demo/x", "job1", pipeline_name="price")
    with PipelineProgress.bind("demo/x", "job1") as prog:
        prog.mark_running()
        prog.enter_step("load")
        prog.complete_step()
        prog.enter_step("execute")
        prog.tick_execute(2, 2)
        prog.complete_step()
        prog.enter_step("report")
        prog.complete_step()
        prog.complete(result={"version_id": "v3", "message": "price 已完成"})

    env = WorkbenchRunLauncher.get_run_progress(strategy_name="demo/x", job_id="job1")
    assert env is not None
    assert env["status"] == "completed"
    assert env["phase"] == "completed"
    assert env["pipeline_name"] == "price"
    assert env["result"]["version_id"] == "v3"
    assert "load" in [x["name"] for x in env["completed_steps"]]

    step = WorkbenchRunLauncher.get_step_progress(
        strategy_name="demo/x",
        normalized_step="price",
        job_id="job1",
    )
    assert step["status"] == "completed"
    assert step["version_id"] == "v3"

    assert (
        WorkbenchRunLauncher.get_step_progress(
            strategy_name="demo/x",
            normalized_step="enum",
            job_id="job1",
        )
        is None
    )


@patch(
    "core.infra.task_guard.task_guard.TaskGuard.read_status",
    return_value={"busy": False},
)
@patch(
    "core.bff.APIs.strategy.routes.runner.workbench_run.DiscoveryService.find_strategy",
    return_value=None,
)
@patch.object(WorkbenchRunLauncher, "_find_any", return_value=None)
def test_submit_unknown_strategy(_find_any, _find, _pipe):
    out = WorkbenchRunLauncher.submit(
        strategy_name="missing",
        step="enum",
        api_settings={},
        force_refresh=False,
    )
    assert out["is_triggered"] is False
    assert "不存在" in out["reason"]


@patch(
    "core.infra.task_guard.task_guard.TaskGuard.read_status",
    return_value={"busy": True, "kind": "tag_run"},
)
@patch(
    "core.bff.APIs.strategy.routes.runner.workbench_run.DiscoveryService.find_strategy",
)
def test_submit_task_busy(mock_find, _pipe):
    mock_find.return_value = MagicMock()
    out = WorkbenchRunLauncher.submit(
        strategy_name="demo/x",
        step="enum",
        api_settings={},
        force_refresh=False,
    )
    assert out["is_triggered"] is False
    assert "tag_run" in out["reason"]
