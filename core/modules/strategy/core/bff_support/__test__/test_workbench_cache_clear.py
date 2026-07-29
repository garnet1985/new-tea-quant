"""Tests for workbench cache clear (V2-11 / V2-12)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.modules.strategy.core.bff_support.workbench_cache_clear import (
    WorkbenchCacheClear,
)


@patch.object(WorkbenchCacheClear, "_snapshot_model")
def test_clear_all(mock_model):
    model = MagicMock()
    model.delete_all.return_value = 4
    mock_model.return_value = model

    out = WorkbenchCacheClear.clear_all()
    assert out["ok"] is True
    assert out["deleted_count"] == 4
    model._ensure_table_ready.assert_called_once()
    model.delete_all.assert_called_once()


@patch.object(WorkbenchCacheClear, "_snapshot_model", return_value=None)
def test_clear_all_storage_unavailable(_mock_model):
    out = WorkbenchCacheClear.clear_all()
    assert out["ok"] is False
    assert out["error"] == "存储不可用"


@patch.object(WorkbenchCacheClear, "_snapshot_model")
def test_clear_by_version_success(mock_model):
    model = MagicMock()
    model.load_by_strategy_version.return_value = {"version": 2}
    model.delete_version_row.return_value = 1
    mock_model.return_value = model

    out = WorkbenchCacheClear.clear_by_version("demo/x", 2)
    assert out["ok"] is True
    assert out["deleted"] is True
    assert out["version_id"] == "v2"
    model.delete_version_row.assert_called_once_with("demo/x", 2)


@patch.object(WorkbenchCacheClear, "_snapshot_model")
def test_clear_by_version_missing(mock_model):
    model = MagicMock()
    model.load_by_strategy_version.return_value = None
    mock_model.return_value = model

    out = WorkbenchCacheClear.clear_by_version("demo/x", 9)
    assert out["ok"] is False
    assert out["error"] == "快照不存在"


def test_clear_by_version_invalid_params():
    out = WorkbenchCacheClear.clear_by_version("", 0)
    assert out["ok"] is False
    assert out["error"] == "参数无效"
