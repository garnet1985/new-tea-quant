"""CalendarService latest completed 推导与 data.json as-of。"""
from unittest.mock import MagicMock, patch

import pytest

from core.modules.data_manager.core.data_services.calendar.calendar_service import CalendarService

pytestmark = pytest.mark.force_run


def _service_with_calendar(calendar_model) -> CalendarService:
    dm = MagicMock()
    dm.get_table.return_value = calendar_model
    return CalendarService(dm)


def test_derive_completed_uses_cal_max_when_before_as_of():
    cal = MagicMock()
    cal.load_db_latest_completed_trading_date.return_value = "20250520"
    svc = _service_with_calendar(cal)

    assert svc._derive_completed_from_trade_calendar(as_of_date="20250524") == "20250520"
    cal.load_previous_open_date_before.assert_not_called()


def test_derive_completed_pushes_back_when_cal_max_equals_as_of():
    cal = MagicMock()
    cal.load_db_latest_completed_trading_date.return_value = "20250524"
    cal.load_previous_open_date_before.return_value = "20250523"
    svc = _service_with_calendar(cal)

    assert svc._derive_completed_from_trade_calendar(as_of_date="20250524") == "20250523"
    cal.load_previous_open_date_before.assert_called_once_with("20250524")


def test_resolve_prefers_trade_calendar_over_real_world():
    cal = MagicMock()
    cal.load_db_latest_completed_trading_date.return_value = "20250520"
    svc = _service_with_calendar(cal)

    with patch.object(
        svc, "get_real_world_latest_completed_trading_date", return_value="20250521"
    ) as rw:
        date, source = svc._resolve_raw_latest_completed(as_of_date="20250524")

    assert date == "20250520"
    assert source == "trade_calendar"
    rw.assert_not_called()


def test_get_latest_completed_uses_data_json_override():
    cal = MagicMock()
    cal.load_db_latest_completed_trading_date.return_value = "20260610"
    svc = _service_with_calendar(cal)

    with patch(
        "core.modules.data_manager.core.data_services.calendar.calendar_service.ProjectContext.config.get_as_of_latest_completed_trading_date",
        return_value="20260101",
    ):
        assert svc.get_latest_completed_trading_date(as_of_date="20260611") == "20260101"


def test_get_latest_completed_falls_back_without_config():
    cal = MagicMock()
    cal.load_db_latest_completed_trading_date.return_value = "20250520"
    svc = _service_with_calendar(cal)

    with patch(
        "core.modules.data_manager.core.data_services.calendar.calendar_service.ProjectContext.config.get_as_of_latest_completed_trading_date",
        return_value=None,
    ):
        assert svc.get_latest_completed_trading_date(as_of_date="20250524") == "20250520"


def test_fetch_with_fallback_uses_registered_fetcher():
    cal = MagicMock()
    svc = _service_with_calendar(cal)
    CalendarService.register_real_world_fetcher(lambda: ("20250519", "sina"))
    try:
        date, provider = svc._fetch_with_fallback()
        assert date == "20250519"
        assert provider == "sina"
    finally:
        CalendarService.register_real_world_fetcher(None)


def test_fetch_with_fallback_guesses_without_fetcher():
    cal = MagicMock()
    svc = _service_with_calendar(cal)
    CalendarService.register_real_world_fetcher(None)
    date, provider = svc._fetch_with_fallback()
    assert provider == "guess"
    assert len(date) == 8
