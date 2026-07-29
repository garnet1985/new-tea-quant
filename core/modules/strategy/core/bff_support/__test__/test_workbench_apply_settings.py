"""Tests for workbench apply-settings (V2-09)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from core.modules.strategy.core.bff_support.workbench_apply_settings import (
    WorkbenchApplySettings,
)


@patch.object(WorkbenchApplySettings, "_write_settings_py")
@patch.object(WorkbenchApplySettings, "_backup_settings_file")
@patch.object(WorkbenchApplySettings, "_snapshot_model")
@patch(
    "core.modules.strategy.core.bff_support.workbench_apply_settings.WorkbenchSnapshots.fetch_by_version"
)
def test_apply_success(mock_fetch, mock_model, mock_backup, mock_write):
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
    model = MagicMock()
    model.touch_version_updated_at.return_value = 1
    mock_model.return_value = model

    out, err = WorkbenchApplySettings.apply(
        strategy_name="demo/x", version=3, pretty=True
    )
    assert err is None
    assert out["applied"] is True
    assert out["version_id"] == "v3"
    mock_backup.assert_called_once_with("demo/x")
    mock_write.assert_called_once()
    model.touch_version_updated_at.assert_called_once_with("demo/x", 3)


@patch(
    "core.modules.strategy.core.bff_support.workbench_apply_settings.WorkbenchSnapshots.fetch_by_version",
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
