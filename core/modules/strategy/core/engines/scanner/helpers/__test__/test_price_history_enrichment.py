"""price_history_enrichment 行为测。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from core.modules.strategy.core.engines.scanner.helpers import price_history_enrichment as mod

pytestmark = pytest.mark.force_run


def test_calculate_statistics_win_loss():
    stats = mod._calculate_statistics(
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
    assert mod._latest_price_version_dir("") is None


def test_latest_price_version_dir_from_meta(tmp_path: Path):
    root = tmp_path / "price"
    version = root / "3"
    version.mkdir(parents=True)
    (root / "meta.json").write_text(
        json.dumps({"next_output_version": 4}), encoding="utf-8"
    )

    from core.infra.project_context import ProjectContext
    from core.modules.strategy.core.services.discovery import DiscoveryService

    with (
        patch.object(DiscoveryService, "resolve_strategy_folder", return_value="demo"),
        patch.object(
            ProjectContext.path,
            "get_strategy_simulation_price_directory",
            return_value=root,
        ),
    ):
        got = mod._latest_price_version_dir("demo")
    assert got == version


def test_build_price_history_without_artifacts():
    with patch.object(mod, "_latest_price_version_dir", return_value=None):
        out = mod.build_price_history_for_adapter("demo", ["000001.SZ"])
    assert out == {"session_summary": None, "by_stock": {}}
