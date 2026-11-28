"""Tests for workbench run launcher (V2-05 / V2-06b)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.bff.APIs.strategy.routes.runner.workbench_run import WorkbenchRunLauncher
from core.modules.strategy.core.services.progress import PipelineProgress


@pytest.fixture(autouse=True)
def progress_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("NTQ_PROGRESS_DIR", str(tmp_path / "progress"))
    monkeypatch.setenv("NTQ_PROGRESS_FLUSH_DELAY", "0")
    from core.infra.progress import Progress

    Progress.reset_for_tests()
    yield tmp_path
    Progress.reset_for_tests()


def test_normalize_step():
    assert WorkbenchRunLauncher.normalize_step("enum") == "enum"
    assert WorkbenchRunLauncher.normalize_step("PRICE") == "price"
    assert WorkbenchRunLauncher.normalize_step("portfolio") == "portfolio"
    assert WorkbenchRunLauncher.normalize_step("capital") is None
    assert WorkbenchRunLauncher.normalize_step("nope") is None


def test_pipeline_progress_roundtrip_via_launcher():
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


@patch(
    "core.bff.APIs.strategy.routes.runner.workbench_run.Strategy.find",
    return_value=None,
)
def test_submit_unknown_strategy(_find):
    out = WorkbenchRunLauncher.submit(
        strategy_name="missing",
        step="enum",
        api_settings={},
        force_refresh=False,
    )
    assert out["is_triggered"] is False
    assert "不存在" in out["reason"]


@patch(
    "core.infra.job_pipeline.JobPipeline.has_running_job",
    return_value=True,
)
@patch(
    "core.bff.APIs.strategy.routes.runner.workbench_run.Strategy.find",
)
def test_submit_task_busy(mock_find, _busy, tmp_path, monkeypatch):
    mock_find.return_value = {"key": "demo", "is_enabled": True}
    monkeypatch.setenv("NTQ_USERSPACE", str(tmp_path / "userspace"))
    # ProjectContext may not read NTQ_USERSPACE — patch queue path instead
    qfile = tmp_path / "job_pipeline_queue.json"
    monkeypatch.setattr(
        "core.infra.job_pipeline.core.queue_store.queue_path",
        lambda: qfile,
    )
    out = WorkbenchRunLauncher.submit(
        strategy_name="demo/x",
        step="enum",
        api_settings={},
        force_refresh=False,
    )
    assert out["is_triggered"] is False
    assert out.get("queued") is True
    assert out.get("job_id")
