"""Tests for userspace cache cleanup."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from core.infra.system_actions.cache_cleanup.cache_cleanup import run_cache_cleanup


@pytest.fixture
def userspace_layout(tmp_path, monkeypatch):
    strategies = tmp_path / "strategies" / "demo" / "nested" / "my_strategy"
    sim = strategies / "results" / "simulations" / "enum" / "v1"
    scan = strategies / "results" / "scan" / "20251231"
    ntq = tmp_path / ".ntq" / "runtime"
    sim.mkdir(parents=True)
    scan.mkdir(parents=True)
    ntq.mkdir(parents=True)
    (sim / "out.json").write_text("{}", encoding="utf-8")
    (scan / "opportunities.csv").write_text("x", encoding="utf-8")
    (ntq / "pipeline_active.json").write_text("{}", encoding="utf-8")
    (strategies / "settings.py").write_text("settings = {}\n", encoding="utf-8")
    (strategies / "strategy_worker.py").write_text(
        "class StrategyWorker:\n    pass\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "core.infra.system_actions.cache_cleanup.cache_cleanup.PathManager.strategies_root",
        lambda: tmp_path / "strategies",
    )
    monkeypatch.setattr(
        "core.infra.system_actions.cache_cleanup.cache_cleanup.PathManager.userspace_ntq",
        lambda: tmp_path / ".ntq",
    )
    monkeypatch.setattr(
        "core.infra.system_actions.cache_cleanup.cache_cleanup.PathManager.invalidate_userspace_cache",
        lambda: None,
    )
    return tmp_path


def test_run_cache_cleanup_rejects_when_pipeline_busy(userspace_layout):
    with patch(
        "core.infra.system_actions.cache_cleanup.cache_cleanup.read_pipeline_status",
        return_value={"busy": True, "label": "Tag 计算中", "kind": "tag_run"},
    ):
        out = run_cache_cleanup(clear_userspace_ntq=True)
    assert out["ok"] is False
    assert out["error"] == "pipeline_busy"
    assert (userspace_layout / ".ntq").exists()


def test_run_cache_cleanup_selected_targets(userspace_layout):
    with patch(
        "core.infra.system_actions.cache_cleanup.cache_cleanup.read_pipeline_status",
        return_value={"busy": False},
    ), patch(
        "core.infra.system_actions.cache_cleanup.cache_cleanup.clear_workbench_db_cache",
        return_value=2,
    ) as mock_db:
        out = run_cache_cleanup(
            clear_db_cache=True,
            clear_backtest_results=True,
            clear_scan_results=True,
            clear_userspace_ntq=True,
        )
    assert out == {"ok": True, "message": "缓存已经全部清理"}
    mock_db.assert_called_once()
    assert not (userspace_layout / "strategies" / "demo" / "nested" / "my_strategy" / "results" / "simulations").exists()
    assert not (userspace_layout / "strategies" / "demo" / "nested" / "my_strategy" / "results" / "scan").exists()
    assert not (userspace_layout / ".ntq").exists()


def test_run_cache_cleanup_nothing_selected():
    out = run_cache_cleanup()
    assert out["ok"] is False
    assert out["error"] == "nothing_selected"
