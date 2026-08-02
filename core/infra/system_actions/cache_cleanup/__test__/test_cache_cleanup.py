"""Tests for userspace cache cleanup."""

from __future__ import annotations

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.force_run

from core.infra.system_actions.cache_cleanup.cache_cleanup import CacheCleanup


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
    (strategies / "strategy.py").write_text(
        "\n".join(
            [
                "from core.modules.strategy.hooks import StrategyHooks",
                "class StrategyHooksImpl(StrategyHooks):",
                "    def scan_opportunity(self, ctx):",
                "        return None",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "core.infra.project_context.core.path_manager.PathManager.get_strategies_root",
        lambda: tmp_path / "strategies",
    )
    monkeypatch.setattr(
        "core.infra.project_context.core.path_manager.PathManager.get_userspace_ntq_directory",
        lambda: tmp_path / ".ntq",
    )
    monkeypatch.setattr(
        "core.infra.project_context.core.path_manager.PathManager.clear_userspace_cache",
        lambda: None,
    )
    return tmp_path


def test_run_cache_cleanup_rejects_when_pipeline_busy(userspace_layout):
    with patch(
        "core.infra.system_actions.cache_cleanup.pipeline_lease.PipelineLease.read_status",
        return_value={"busy": True, "label": "Tag 计算中", "kind": "tag_run"},
    ):
        out = CacheCleanup.run(clear_userspace_ntq=True)
    assert out["ok"] is False
    assert out["error"] == "pipeline_busy"
    assert (userspace_layout / ".ntq").exists()


def test_run_cache_cleanup_selected_targets(userspace_layout):
    with patch(
        "core.infra.system_actions.cache_cleanup.pipeline_lease.PipelineLease.read_status",
        return_value={"busy": False},
    ), patch.object(
        CacheCleanup,
        "clear_workbench_db_cache",
        return_value=2,
    ) as mock_db, patch.object(
        CacheCleanup,
        "_discovered_strategy_keys",
        return_value=["demo/nested/my_strategy"],
    ):
        out = CacheCleanup.run(
            clear_db_cache=True,
            clear_backtest_results=True,
            clear_scan_results=True,
            clear_userspace_ntq=True,
        )
    assert out == {"ok": True, "message": "缓存已经全部清理"}
    mock_db.assert_called_once()
    assert not (
        userspace_layout
        / "strategies"
        / "demo"
        / "nested"
        / "my_strategy"
        / "results"
        / "simulations"
    ).exists()
    assert not (
        userspace_layout
        / "strategies"
        / "demo"
        / "nested"
        / "my_strategy"
        / "results"
        / "scan"
    ).exists()
    assert not (userspace_layout / ".ntq").exists()


def test_run_cache_cleanup_nothing_selected():
    out = CacheCleanup.run()
    assert out["ok"] is False
    assert out["error"] == "nothing_selected"
