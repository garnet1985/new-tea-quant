"""Tests for strategy version implementer (snapshot reads + parse)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.bff.APIs.strategy.routes.version.implementer import StrategyVersionImplementer


def test_parse_version_id():
    assert StrategyVersionImplementer.parse_version_id("v3") == 3
    assert StrategyVersionImplementer.parse_version_id("12") == 12
    assert StrategyVersionImplementer.parse_version_id("0") is None
    assert StrategyVersionImplementer.parse_version_id("") is None
    assert StrategyVersionImplementer.parse_version_id("x") is None


def test_fetch_latest_merges_ui_flags():
    impl = StrategyVersionImplementer()
    row = {"version": 2, "settings_snapshot": {}, "result_report": {}}
    flags = {"has_persisted_snapshot": True, "has_other_versions": False}
    snaps = MagicMock()
    snaps.fetch_latest.return_value = row
    snaps.ui_flags.return_value = flags

    with patch.object(impl, "resolve_strategy_name", return_value="demo/x"):
        impl._WorkbenchSnapshots = snaps
        out_row, out_flags = impl.fetch_latest("demo-key")

    assert out_row is row
    assert out_flags == flags
    snaps.fetch_latest.assert_called_once_with("demo/x")
    snaps.ui_flags.assert_called_once_with("demo/x", row)


def test_fetch_by_version_invalid_id():
    impl = StrategyVersionImplementer()
    impl._WorkbenchSnapshots = MagicMock()
    with patch.object(impl, "resolve_strategy_name", return_value="demo/x"):
        with pytest.raises(ValueError, match="version_id"):
            impl.fetch_by_version(strategy_key_or_name="demo/x", version_id="bad")


def test_fetch_by_version_missing_row():
    impl = StrategyVersionImplementer()
    snaps = MagicMock()
    snaps.fetch_by_version.return_value = None
    impl._WorkbenchSnapshots = snaps
    with patch.object(impl, "resolve_strategy_name", return_value="demo/x"):
        with pytest.raises(FileNotFoundError, match="快照不存在"):
            impl.fetch_by_version(strategy_key_or_name="demo/x", version_id="v9")


def test_list_versions_resolves_name():
    impl = StrategyVersionImplementer()
    snaps = MagicMock()
    snaps.list_dropdown.return_value = [{"version_id": "v1", "version": 1}]
    impl._WorkbenchSnapshots = snaps
    with patch.object(impl, "resolve_strategy_name", return_value="demo/x"):
        items = impl.list_versions("k")
    assert items[0]["version_id"] == "v1"
    snaps.list_dropdown.assert_called_once_with("demo/x")
