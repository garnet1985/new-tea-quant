"""Tests for workbench run launcher / envelope (V2-05 / V2-06)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.modules.strategy.launcher.workbench_run import WorkbenchRunLauncher
from core.modules.strategy.launcher.workbench_run_envelope import (
    get_run_progress,
    get_step_progress_from_envelope,
    run_envelope_mark_phase_completed,
    run_envelope_on_substep_finish,
    seed_workbench_run_envelope,
)


def test_normalize_step():
    assert WorkbenchRunLauncher.normalize_step("enum") == "enum"
    assert WorkbenchRunLauncher.normalize_step("PRICE") == "price"
    assert WorkbenchRunLauncher.normalize_step("capital") == "capital"
    assert WorkbenchRunLauncher.normalize_step("portfolio") is None


def test_envelope_seed_and_progress_roundtrip(tmp_path, monkeypatch):
    from core.modules.strategy.core.services.progress import ProgressRecorder

    def _build(channel, file_key):
        return tmp_path / "progress" / channel / f"{file_key}.json"

    monkeypatch.setattr(ProgressRecorder, "build_path", staticmethod(_build))

    steps = seed_workbench_run_envelope("demo/x", "job1", ["enum", "price"])
    assert [s["step_name"] for s in steps] == ["enum", "price"]
    assert steps[0]["status"] == "pending"

    run_envelope_on_substep_finish("demo/x", "job1", 0, 2, "enum", 3)
    run_envelope_on_substep_finish("demo/x", "job1", 1, 2, "price", 3)
    run_envelope_mark_phase_completed("demo/x", "job1")

    env = get_run_progress(strategy_name="demo/x", job_id="job1")
    assert env is not None
    assert env["phase"] == "completed"
    assert env["steps"][0]["result"]["version_id"] == "v3"

    step = get_step_progress_from_envelope(
        strategy_name="demo/x",
        normalized_step="price",
        job_id="job1",
    )
    assert step["status"] == "completed"
    assert step["version_id"] == "v3"


@patch(
    "core.modules.strategy.launcher.workbench_run.read_pipeline_status",
    return_value={"busy": False},
)
@patch(
    "core.modules.strategy.launcher.workbench_run.DiscoveryService.find_strategy",
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
    "core.modules.strategy.launcher.workbench_run.read_pipeline_status",
    return_value={"busy": True, "kind": "tag_run"},
)
@patch(
    "core.modules.strategy.launcher.workbench_run.DiscoveryService.find_strategy",
)
def test_submit_pipeline_busy(mock_find, _pipe):
    mock_find.return_value = MagicMock()
    out = WorkbenchRunLauncher.submit(
        strategy_name="demo/x",
        step="enum",
        api_settings={},
        force_refresh=False,
    )
    assert out["is_triggered"] is False
    assert "tag_run" in out["reason"]
