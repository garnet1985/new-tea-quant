"""HistoryLoader 行为测。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from core.modules.adapter.contracts import HistoryLoader

pytestmark = pytest.mark.force_run


def test_calculate_statistics_win_loss():
    stats = HistoryLoader._calculate_statistics(
        [
            {"roi": 0.10, "result": "win", "duration_in_days": 2},
            {"roi": -0.05, "result": "loss", "duration_in_days": 4},
        ]
    )
    assert stats["win_count"] == 1
    assert stats["loss_count"] == 1
    assert stats["win_rate"] == 0.5
    assert stats["completed_investments"] == 2
    assert stats["avg_holding_days"] == 3.0


def test_latest_price_version_dir_empty_name():
    assert HistoryLoader._latest_price_version_dir("") is None


def test_latest_price_version_dir_from_meta(tmp_path: Path):
    root = tmp_path / "price"
    version = root / "3"
    version.mkdir(parents=True)
    (root / "meta.json").write_text(
        json.dumps({"next_output_version": 4}), encoding="utf-8"
    )

    with (
        patch(
            "core.modules.strategy.core.services.discovery.DiscoveryService.resolve_strategy_folder",
            return_value="demo",
        ),
        patch(
            "core.infra.project_context.ProjectContext.path.get_strategy_simulation_price_directory",
            return_value=root,
        ),
    ):
        got = HistoryLoader._latest_price_version_dir("demo")
    assert got == version


def test_load_session_summary_missing(tmp_path: Path):
    root = tmp_path / "price"
    version = root / "1"
    version.mkdir(parents=True)
    (root / "meta.json").write_text(
        json.dumps({"next_output_version": 2}), encoding="utf-8"
    )

    with (
        patch(
            "core.modules.strategy.core.services.discovery.DiscoveryService.resolve_strategy_folder",
            return_value="demo",
        ),
        patch(
            "core.infra.project_context.ProjectContext.path.get_strategy_simulation_price_directory",
            return_value=root,
        ),
    ):
        assert HistoryLoader.load_session_summary("demo") is None
