"""Tests for workbench snapshot helpers (V2-01 / V2-03 / V2-08)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.bff.APIs.strategy.helpers.formatting import workbench_snapshot_to_message
from core.bff.APIs.strategy.helpers.workbench_snapshots import WorkbenchSnapshots
from core.modules.strategy.core.enums import SimulateKind
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
    assert row["step_status"]["enum"]["done"] is True
    assert row["step_status"]["price_factor"]["done"] is False
    assert row["step_status"]["portfolio"]["done"] is False


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
                "2": {"created_at": "2024-01-02", "execute_fp": "s", "env_fp": "old-env"},
                "1": {"created_at": "2024-01-01", "execute_fp": "s", "env_fp": "current-env"},
            }
        },
    )
    with patch.object(WorkbenchSnapshots, "_simulations_root", return_value=root), patch.object(
        WorkbenchSnapshots, "_current_env_fp", return_value="current-env"
    ), patch.object(WorkbenchSnapshots, "_retention_cap", return_value=10):
        items = WorkbenchSnapshots.list_dropdown("demo/x")
    assert [i["version_id"] for i in items] == ["v2", "v1"]
    assert items[0]["env_invalid"] is True
    assert items[1]["env_invalid"] is False
    assert items[0]["expires_soon"] is False
    assert items[1]["expires_soon"] is False
    assert items[0]["retention_max"] == 10


def test_expires_soon_vids_at_and_over_cap():
    assert WorkbenchSnapshots.expires_soon_vids(["3", "2", "1"], 10) == set()
    assert WorkbenchSnapshots.expires_soon_vids(["3", "2", "1"], 3) == {"1"}
    assert WorkbenchSnapshots.expires_soon_vids(["5", "4", "3", "2", "1"], 3) == {
        "3",
        "2",
        "1",
    }
    assert WorkbenchSnapshots.expires_soon_vids(
        ["5", "4", "3", "2", "1"], 3, ["1"]
    ) == {"4", "3", "2"}


@patch.object(WorkbenchSnapshots, "_find_strategy")
def test_list_dropdown_pins_first_and_skips_expires(mock_find, tmp_path: Path):
    mock_find.return_value = _info()
    root = tmp_path / "simulations"
    VersionMetaStore.write_root_meta(
        root,
        {
            "pinned": ["1"],
            "registry": {
                "3": {"created_at": "2024-01-03", "execute_fp": "s", "env_fp": "e"},
                "2": {"created_at": "2024-01-02", "execute_fp": "s", "env_fp": "e"},
                "1": {"created_at": "2024-01-01", "execute_fp": "s", "env_fp": "e"},
            },
        },
    )
    (root / "1").mkdir(parents=True)
    (root / "2").mkdir(parents=True)
    (root / "3").mkdir(parents=True)
    with patch.object(WorkbenchSnapshots, "_simulations_root", return_value=root), patch.object(
        WorkbenchSnapshots, "_current_env_fp", return_value="e"
    ), patch.object(WorkbenchSnapshots, "_retention_cap", return_value=3):
        items = WorkbenchSnapshots.list_dropdown("demo/x")
    assert [i["version_id"] for i in items] == ["v1", "v3", "v2"]
    by_id = {i["version_id"]: i for i in items}
    assert by_id["v1"]["pinned"] is True
    assert by_id["v1"]["expires_soon"] is False
    assert by_id["v2"]["pinned"] is False
    assert by_id["v2"]["expires_soon"] is True


@patch.object(WorkbenchSnapshots, "_find_strategy")
def test_list_dropdown_marks_expires_soon(mock_find, tmp_path: Path):
    mock_find.return_value = _info()
    root = tmp_path / "simulations"
    VersionMetaStore.write_root_meta(
        root,
        {
            "registry": {
                "3": {"created_at": "2024-01-03", "execute_fp": "s", "env_fp": "e"},
                "2": {"created_at": "2024-01-02", "execute_fp": "s", "env_fp": "e"},
                "1": {"created_at": "2024-01-01", "execute_fp": "s", "env_fp": "e"},
            }
        },
    )
    with patch.object(WorkbenchSnapshots, "_simulations_root", return_value=root), patch.object(
        WorkbenchSnapshots, "_current_env_fp", return_value="e"
    ), patch.object(WorkbenchSnapshots, "_retention_cap", return_value=3):
        items = WorkbenchSnapshots.list_dropdown("demo/x")
    by_id = {i["version_id"]: i for i in items}
    assert by_id["v1"]["expires_soon"] is True
    assert by_id["v2"]["expires_soon"] is False
    assert by_id["v3"]["expires_soon"] is False
    assert by_id["v1"]["retention_max"] == 3
    assert by_id["v1"]["pinned"] is False


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


@patch.object(WorkbenchSnapshots, "_find_strategy")
def test_step_status_from_artifacts_even_if_cache_payload_missing(
    mock_find, tmp_path: Path
):
    """步进器认产物目录，不依赖 get_cache 能否拼出 result_report。"""
    info = _info()
    mock_find.return_value = info
    root = tmp_path / "simulations"
    VersionMetaStore.register_version(root, "6", execute_fp="s", env_fp="e")
    for name, kind in (
        ("enum", SimulateKind.ENUMERATE),
        ("price", SimulateKind.PRICE_FACTOR),
        ("portfolio", SimulateKind.PORTFOLIO),
    ):
        step_dir = root / "6" / name
        step_dir.mkdir(parents=True)
        (step_dir / RUNTIME_ENV_FILE).write_text("{}", encoding="utf-8")
        VersionMetaStore.mark_step_complete(root, "6", kind)

    with patch.object(WorkbenchSnapshots, "_simulations_root", return_value=root), patch.object(
        WorkbenchSnapshots, "_strategy_folder", return_value=info.folder
    ), patch.object(
        WorkbenchSnapshots,
        "_enrich_row",
        side_effect=lambda name, _info, row: row,
    ), patch(
        "core.bff.APIs.strategy.helpers.workbench_snapshots.SimulationVersionStore.get_cache_by_version_id",
        return_value=None,
    ):
        row = WorkbenchSnapshots.fetch_latest("demo/random/random_v1_null_baseline")

    assert row is not None
    assert row["step_status"] == {
        "enum": {"done": True},
        "price_factor": {"done": True},
        "portfolio": {"done": True},
    }
    msg = workbench_snapshot_to_message(row)
    assert msg["step_status"]["price_factor"]["done"] is True
    assert msg["step_status"]["portfolio"]["done"] is True
