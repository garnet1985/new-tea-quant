"""Tests for workbench snapshot helpers (V2-01 / V2-03 / V2-08)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from core.modules.strategy.core.bff_support.workbench_snapshots import WorkbenchSnapshots
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    StrategyInfo,
)


def _info(path: str = "demo/random/random_v1_null_baseline") -> StrategyInfo:
    return StrategyInfo(
        unique_relative_path=path,
        strategy_file=Path(f"/tmp/{path}/strategy.py"),
        settings_file=Path(f"/tmp/{path}/settings.py"),
        folder=Path(f"/tmp/{path}"),
        key="random_v1",
        display_name="demo",
        is_enabled=True,
        settings={"is_enabled": True, "meta": {"key": "random_v1"}, "core": {"seed": 1}},
        hooks_class=type("H", (), {}),
        hooks_module_path="mod",
    )


def test_parse_version_id():
    assert WorkbenchSnapshots.parse_version_id("v3") == 3
    assert WorkbenchSnapshots.parse_version_id("12") == 12
    assert WorkbenchSnapshots.parse_version_id("v0") is None
    assert WorkbenchSnapshots.parse_version_id("") is None


@patch.object(WorkbenchSnapshots, "_snapshot_model")
@patch.object(WorkbenchSnapshots, "_find_strategy")
def test_fetch_latest_cold_start(mock_find, mock_model):
    mock_find.return_value = _info()
    model = MagicMock()
    model.list_by_strategy.return_value = []
    mock_model.return_value = model

    row = WorkbenchSnapshots.fetch_latest("demo/random/random_v1_null_baseline")
    assert row is not None
    assert row["version"] == 0
    assert row["settings_snapshot"]["core"]["seed"] == 1
    assert row["result_report"] == {}


@patch.object(WorkbenchSnapshots, "_snapshot_model")
@patch.object(WorkbenchSnapshots, "_find_strategy")
def test_fetch_latest_merges_settings_diff(mock_find, mock_model):
    mock_find.return_value = _info()
    model = MagicMock()
    model.list_by_strategy.return_value = [
        {
            "version": 2,
            "settings_diff": {"core": {"seed": 99}},
            "result_report": {"enum": {"enumMetrics": {"totalOpportunities": 3}}},
        }
    ]
    mock_model.return_value = model

    row = WorkbenchSnapshots.fetch_latest("demo/random/random_v1_null_baseline")
    assert row["version"] == 2
    assert row["settings_snapshot"]["core"]["seed"] == 99
    assert row["result_report"]["enum"]["opportunities"] == 3


@patch.object(WorkbenchSnapshots, "_snapshot_model")
def test_list_dropdown(mock_model):
    model = MagicMock()
    model.list_by_strategy.return_value = [
        {"version": 2, "created_at": None, "updated_at": None},
        {"version": 1, "created_at": None, "updated_at": None},
    ]
    mock_model.return_value = model
    items = WorkbenchSnapshots.list_dropdown("demo/x")
    assert [i["version_id"] for i in items] == ["v2", "v1"]


@patch.object(WorkbenchSnapshots, "_find_strategy", return_value=None)
def test_fetch_latest_missing_strategy(_mock_find):
    assert WorkbenchSnapshots.fetch_latest("missing") is None
