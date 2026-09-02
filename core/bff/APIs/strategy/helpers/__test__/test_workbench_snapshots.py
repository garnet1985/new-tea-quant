"""Tests for workbench snapshot helpers (V2-01 / V2-03 / V2-08)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.bff.APIs.strategy.helpers.workbench_snapshots import WorkbenchSnapshots
from core.modules.strategy.core.services.artifacts.consts import (
    EFFECTIVE_SETTINGS_FILE,
    RUNTIME_ENV_FILE,
    SETTINGS_FILE,
)
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    StrategyInfo,
)


def _info(path: str = "demo/random/random_v1_null_baseline") -> StrategyInfo:
    folder = Path(f"/tmp/{path}")
    return StrategyInfo(
        unique_relative_path=path,
        strategy_file=folder / "strategy.py",
        settings_file=folder / "settings.py",
        folder=folder,
        key="random_v1",
        display_name="demo",
        is_enabled=True,
        settings={
            "is_enabled": True,
            "meta": {"key": "random_v1"},
            "core": {"seed": 1},
            "data": {"base": {"data_key": "stock.kline.daily"}},
            "simulation": {
                "execution": {
                    "mode": "entity_based",
                    "start_date": "20200101",
                    "end_date": "20201231",
                }
            },
        },
        hooks_class=type("H", (), {}),
        hooks_module_path="mod",
    )


def test_parse_version_id():
    assert WorkbenchSnapshots.parse_version_id("v3") == 3
    assert WorkbenchSnapshots.parse_version_id("12") == 12
    assert WorkbenchSnapshots.parse_version_id("v0") is None
    assert WorkbenchSnapshots.parse_version_id("") is None


@patch.object(WorkbenchSnapshots, "_find_strategy")
def test_fetch_latest_cold_start(mock_find):
    mock_find.return_value = _info()
    with patch.object(WorkbenchSnapshots, "_simulations_root") as mock_root:
        mock_root.return_value = Path("/tmp/empty/simulations")
        with patch.object(
            VersionMetaStore, "list_version_ids", return_value=[]
        ):
            row = WorkbenchSnapshots.fetch_latest("demo/random/random_v1_null_baseline")
    assert row is not None
    assert row["version"] == 0
    assert row["settings_snapshot"]["core"]["seed"] == 1
    assert row["disk_settings"]["core"]["seed"] == 1
    assert row["effective_settings"] == {}
    assert row["result_report"] == {}


@patch.object(WorkbenchSnapshots, "_find_strategy")
def test_fetch_latest_reads_disk_version(mock_find, tmp_path: Path):
    info = _info()
    mock_find.return_value = info
    root = tmp_path / "simulations"
    enum_dir = root / "2" / "enum"
    enum_dir.mkdir(parents=True)
    (enum_dir / RUNTIME_ENV_FILE).write_text("{}", encoding="utf-8")
    (root / "2" / EFFECTIVE_SETTINGS_FILE).write_text(
        json.dumps({"core": {"seed": 99}}),
        encoding="utf-8",
    )
    VersionMetaStore.register_version(root, "2", execute_fp="s", env_fp="e")

    with patch.object(WorkbenchSnapshots, "_simulations_root", return_value=root), patch.object(
        WorkbenchSnapshots, "_strategy_folder", return_value=info.folder
    ), patch.object(
        WorkbenchSnapshots,
        "_enrich_row",
        side_effect=lambda name, _info, row: row,
    ):
        row = WorkbenchSnapshots.fetch_latest("demo/random/random_v1_null_baseline")

    assert row is not None
    assert row["version"] == 2
    assert row["settings_snapshot"]["core"]["seed"] == 99
    assert row["disk_settings"]["core"]["seed"] == 1
    assert row["effective_settings"]["core"]["seed"] == 99


@patch.object(WorkbenchSnapshots, "_find_strategy")
def test_fetch_latest_prefers_archived_full_settings(mock_find, tmp_path: Path):
    info = _info()
    mock_find.return_value = info
    root = tmp_path / "simulations"
    enum_dir = root / "3" / "enum"
    enum_dir.mkdir(parents=True)
    (enum_dir / RUNTIME_ENV_FILE).write_text("{}", encoding="utf-8")
    (root / "3" / SETTINGS_FILE).write_text(
        json.dumps({"core": {"seed": 7}, "analysis": {"enabled": True}}),
        encoding="utf-8",
    )
    (root / "3" / EFFECTIVE_SETTINGS_FILE).write_text(
        json.dumps({"core": {"seed": 7}}),
        encoding="utf-8",
    )
    VersionMetaStore.register_version(root, "3", execute_fp="s", env_fp="e")

    with patch.object(WorkbenchSnapshots, "_simulations_root", return_value=root), patch.object(
        WorkbenchSnapshots, "_strategy_folder", return_value=info.folder
    ), patch.object(
        WorkbenchSnapshots,
        "_enrich_row",
        side_effect=lambda name, _info, row: row,
    ):
        row = WorkbenchSnapshots.fetch_latest("demo/random/random_v1_null_baseline")

    assert row is not None
    assert row["version"] == 3
    assert row["settings_snapshot"]["core"]["seed"] == 7
    assert row["settings_snapshot"]["analysis"]["enabled"] is True
    assert row["disk_settings"]["core"]["seed"] == 1
    assert "analysis" not in row["effective_settings"]


@patch.object(WorkbenchSnapshots, "_find_strategy")
def test_list_dropdown_from_registry(mock_find, tmp_path: Path):
    mock_find.return_value = _info()
    root = tmp_path / "simulations"
    VersionMetaStore.write_root_meta(
        root,
        {
            "registry": {
                "2": {"created_at": "2024-01-02", "execute_fp": "s", "env_fp": "e"},
                "1": {"created_at": "2024-01-01", "execute_fp": "s", "env_fp": "e"},
            }
        },
    )
    with patch.object(WorkbenchSnapshots, "_simulations_root", return_value=root):
        items = WorkbenchSnapshots.list_dropdown("demo/x")
    assert [i["version_id"] for i in items] == ["v2", "v1"]


@patch.object(WorkbenchSnapshots, "_find_strategy", return_value=None)
def test_fetch_latest_missing_strategy(_mock_find):
    assert WorkbenchSnapshots.fetch_latest("missing") is None


@patch.object(WorkbenchSnapshots, "_find_strategy")
def test_ui_flags_counts_disk_versions(mock_find, tmp_path: Path):
    mock_find.return_value = _info()
    root = tmp_path / "simulations"
    VersionMetaStore.register_version(root, "1", execute_fp="s", env_fp="e")
    VersionMetaStore.register_version(root, "2", execute_fp="s", env_fp="e")
    with patch.object(WorkbenchSnapshots, "_simulations_root", return_value=root):
        flags = WorkbenchSnapshots.ui_flags(
            "demo/x",
            {"version": 2, "settings_snapshot": {}, "result_report": {}},
        )
    assert flags == {
        "has_persisted_snapshot": True,
        "has_other_versions": True,
        "env_invalid": False,
    }
