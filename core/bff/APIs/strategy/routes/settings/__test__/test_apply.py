"""Tests for settings apply (V2-09)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from core.bff.APIs.strategy.helpers.settings_occupancy import SettingsOccupancy
from core.bff.APIs.strategy.routes.settings.apply import WorkbenchApplySettings


@patch.object(
    SettingsOccupancy,
    "read",
    return_value={
        "settings_rev": "rev-after",
        "disk_settings": {"core": {"n": 1}},
        "execute_settings": {"core": {"n": 1}},
    },
)
@patch.object(SettingsOccupancy, "require_match", return_value={})
@patch.object(WorkbenchApplySettings, "_write_settings_py")
@patch.object(WorkbenchApplySettings, "_backup_settings_file")
@patch(
    "core.bff.APIs.strategy.routes.settings.apply.WorkbenchSnapshots.fetch_by_version"
)
def test_apply_success(mock_fetch, mock_backup, mock_write, _match, mock_read):
    mock_fetch.return_value = {
        "version": 3,
        "settings_snapshot": {
            "is_enabled": True,
            "meta": {"key": "demo"},
            "data": {"base": {"data_key": "stock.kline.daily", "params": {}, "indicators": {}}},
            "goal": {},
            "simulation": {
                "execution": {
                    "mode": "entity_based",
                    "start_date": "20200101",
                    "end_date": "20201231",
                }
            },
        },
    }

    out, err = WorkbenchApplySettings.apply(
        strategy_name="demo/x", version=3, pretty=True
    )
    assert err is None
    assert out["applied"] is True
    assert out["version_id"] == "v3"
    assert out["settings_rev"] == "rev-after"
    mock_backup.assert_called_once_with("demo/x")
    mock_write.assert_called_once()
    mock_read.assert_called_once_with("demo/x")


@patch.object(
    SettingsOccupancy,
    "read",
    return_value={
        "settings_rev": "rev-after",
        "disk_settings": {},
        "execute_settings": {},
    },
)
@patch.object(SettingsOccupancy, "require_match", return_value={})
@patch.object(WorkbenchApplySettings, "_write_settings_py")
@patch.object(WorkbenchApplySettings, "_backup_settings_file")
def test_persist_editor_settings_success(mock_backup, mock_write, _match, _read):
    out, err = WorkbenchApplySettings.persist_editor_settings(
        strategy_name="demo/x",
        settings={
            "is_enabled": True,
            "meta": {"key": "demo"},
            "data": {"base": {"data_key": "stock.kline.daily", "params": {}, "indicators": {}}},
            "goal": {},
            "simulation": {
                "execution": {
                    "mode": "entity_based",
                    "start_date": "20200101",
                    "end_date": "20201231",
                }
            },
        },
    )
    assert err is None
    assert out["settings_rev"] == "rev-after"
    mock_backup.assert_called_once_with("demo/x")
    mock_write.assert_called_once()


def test_persist_editor_settings_skips_empty():
    out, err = WorkbenchApplySettings.persist_editor_settings(
        strategy_name="demo/x", settings={}
    )
    assert out is None
    assert err is None


@patch.object(SettingsOccupancy, "require_match")
def test_persist_editor_settings_propagates_conflict(mock_match):
    from core.bff.APIs.strategy.helpers.settings_occupancy import SettingsFileConflict

    mock_match.side_effect = SettingsFileConflict(
        {"settings_rev": "new", "disk_settings": {"a": 1}, "execute_settings": {}}
    )
    with pytest.raises(SettingsFileConflict):
        WorkbenchApplySettings.persist_editor_settings(
            strategy_name="demo/x",
            settings={"is_enabled": True},
            expected_rev="old",
        )


@patch(
    "core.bff.APIs.strategy.routes.settings.apply.WorkbenchSnapshots.fetch_by_version",
    return_value=None,
)
def test_apply_missing_snapshot(_mock_fetch):
    out, err = WorkbenchApplySettings.apply(strategy_name="demo/x", version=1)
    assert out is None
    assert err == "快照不存在"


def test_apply_invalid_params():
    out, err = WorkbenchApplySettings.apply(strategy_name="", version=1)
    assert out is None
    assert err == "参数无效"


def test_atomic_write_roundtrip(tmp_path):
    target = tmp_path / "settings.py"
    WorkbenchApplySettings._atomic_write_text(target, "settings = {}\n")
    assert target.read_text(encoding="utf-8") == "settings = {}\n"
