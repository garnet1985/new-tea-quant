"""CalendarService latest completed 推导与截断（不依赖 DB / 网络）。"""
from unittest.mock import MagicMock, patch

from core.modules.data_manager.data_services.calendar.calendar_service import CalendarService


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


def test_derive_completed_empty_when_today_open_but_no_previous():
    cal = MagicMock()
    cal.load_db_latest_completed_trading_date.return_value = "20250524"
    cal.load_previous_open_date_before.return_value = ""
    svc = _service_with_calendar(cal)

    assert svc._derive_completed_from_trade_calendar(as_of_date="20250524") == ""


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


def test_resolve_falls_back_to_real_world_when_calendar_empty():
    cal = MagicMock()
    cal.load_db_latest_completed_trading_date.return_value = ""
    svc = _service_with_calendar(cal)

    with patch.object(
        svc, "get_real_world_latest_completed_trading_date", return_value="20250521"
    ):
        date, source = svc._resolve_raw_latest_completed(as_of_date="20250524")

    assert date == "20250521"
    assert source == "real_world"


@patch(
    "core.modules.data_manager.data_services.calendar.calendar_service.ConfigManager.get_default_end_date",
    return_value="20251231",
)
def test_apply_default_end_date_cap_when_over(_mock_cap):
    svc = _service_with_calendar(MagicMock())

    assert svc._apply_default_end_date_cap("20260115", source="trade_calendar") == "20251231"


@patch(
    "core.modules.data_manager.data_services.calendar.calendar_service.ConfigManager.get_default_end_date",
    return_value="20251231",
)
def test_get_latest_completed_applies_cap(_mock_cap):
    cal = MagicMock()
    cal.load_db_latest_completed_trading_date.return_value = "20260115"
    svc = _service_with_calendar(cal)

    assert svc.get_latest_completed_trading_date(as_of_date="20260120") == "20251231"


@patch(
    "core.modules.data_manager.data_services.calendar.calendar_service.ConfigManager.get_default_end_date",
    return_value="20251231",
)
def test_get_latest_completed_skips_cap_when_disabled(_mock_cap):
    cal = MagicMock()
    cal.load_db_latest_completed_trading_date.return_value = "20260115"
    svc = _service_with_calendar(cal)

    assert (
        svc.get_latest_completed_trading_date(
            as_of_date="20260120",
            apply_default_end_date_cap=False,
        )
        == "20260115"
    )
