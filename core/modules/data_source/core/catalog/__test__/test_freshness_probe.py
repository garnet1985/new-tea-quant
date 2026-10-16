"""Tests for UI freshness evaluation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.modules.data_source.core.catalog.freshness_probe import _resolve_freshness_end_date
from core.modules.data_source.core.service.date_range.date_range_service import needs_renew_work


class _UnreadyManager:
    _data_service = None
    _initialized = False

    @property
    def service(self):
        raise RuntimeError("DataManager 未初始化，请先调用 initialize()")


def test_freshness_end_date_ignores_unready_manager(monkeypatch):
    monkeypatch.setattr(
        "core.modules.data_source.core.service.renew_progress.ProjectContext.config.get_as_of_latest_completed_trading_date",
        lambda: "20260101",
    )
    monkeypatch.setattr(
        "core.modules.data_source.core.service.renew_progress.member_end_cap",
        lambda: None,
    )
    assert _resolve_freshness_end_date(_UnreadyManager()) == "20260101"


def test_freshness_end_date_stops_at_the_member_window(monkeypatch):
    monkeypatch.setattr(
        "core.modules.data_source.core.service.renew_progress.ProjectContext.config.get_as_of_latest_completed_trading_date",
        lambda: "20260101",
    )
    monkeypatch.setattr(
        "core.modules.data_source.core.service.renew_progress.member_end_cap",
        lambda: "20251231",
    )
    assert _resolve_freshness_end_date(_UnreadyManager()) == "20251231"


def test_needs_renew_work_refresh_stock_list_when_table_has_rows():
    dm = MagicMock()
    model = MagicMock()
    model.load_one.return_value = {"id": "000001.SZ"}
    dm.get_table.return_value = model

    config = MagicMock()
    config.get_renew_mode.return_value = __import__(
        "core.modules.data_source.core.enums", fromlist=["UpdateMode"]
    ).UpdateMode.REFRESH
    config.get_table_name.return_value = "sys_data_stock_list"
    config.is_per_entity.return_value = False
    config.get_needs_stock_grouping.return_value = None

    context = {
        "config": config,
        "data_manager": dm,
        "latest_completed_trading_date": "20251231",
        "dependencies": {},
    }

    with patch(
        "core.modules.data_source.core.service.date_range.date_range_service.DateRangeService.compute_last_update_map",
        return_value={},
    ), patch(
        "core.modules.data_source.core.service.date_range.date_range_service.DateRangeService.compute_entity_date_ranges",
        return_value={"_global": ("20230101", "20251231")},
    ):
        assert needs_renew_work(context, source_key="stock_list") is False


def test_needs_renew_work_rolling_cpi_caught_up_when_db_ahead_of_effective_end():
    config = MagicMock()
    config.get_renew_mode.return_value = __import__(
        "core.modules.data_source.core.enums", fromlist=["UpdateMode"]
    ).UpdateMode.ROLLING
    config.get_date_format.return_value = "month"
    config.is_per_entity.return_value = False
    config.get_needs_stock_grouping.return_value = False

    context = {
        "config": config,
        "data_manager": MagicMock(),
        "latest_completed_trading_date": "20251231",
        "dependencies": {},
    }

    with patch(
        "core.modules.data_source.core.service.date_range.date_range_service.DateRangeService.compute_last_update_map",
        return_value={"_global": "202601"},
    ), patch(
        "core.modules.data_source.core.service.date_range.date_range_service.DateRangeService.compute_entity_date_ranges",
        return_value={"_global": ("202301", "202512")},
    ):
        assert needs_renew_work(context, source_key="cpi") is False
