"""Tests for UI freshness evaluation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.modules.data_source.core.catalog.freshness_probe import (
    _resolve_freshness_end_date,
    evaluate_update_status,
)
from core.modules.data_source.core.service.date_range.date_range_service import needs_renew_work


def test_resolve_freshness_end_aligns_configured_as_of_to_calendar():
    dm = MagicMock()
    dm.service.calendar._derive_completed_from_trade_calendar.return_value = "20251231"

    with patch(
        "core.modules.data_source.core.catalog.freshness_probe.ConfigManager.get_as_of_latest_completed_trading_date",
        return_value="20260101",
    ):
        assert _resolve_freshness_end_date(dm) == "20251231"


def test_needs_renew_work_refresh_stock_list_when_table_has_rows():
    dm = MagicMock()
    model = MagicMock()
    model.load_one.return_value = {"id": "000001.SZ"}
    dm.get_table.return_value = model

    config = MagicMock()
    config.get_renew_mode.return_value = __import__(
        "core.modules.data_source.core.enums", fromlist=["UpdateMode"]
    ).UpdateMode.REFRESH
    config.get_table_name.return_value = "sys_stock_list"
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
