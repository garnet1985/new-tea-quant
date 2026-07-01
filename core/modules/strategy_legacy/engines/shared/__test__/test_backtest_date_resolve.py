"""backtest / tag 日期解析与 latest completed 截断。"""
from unittest.mock import MagicMock, patch

from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.shared.helpers.backtest_date_resolve import (
    SOURCE_LATEST_TRADING_DAY,
    SOURCE_SETTINGS,
    resolve_backtest_end_date,
    resolve_latest_completed_trading_date,
)


def test_resolve_latest_completed_delegates_to_calendar_service():
    cal = MagicMock()
    cal.get_latest_completed_trading_date.return_value = "20250520"
    dm = MagicMock()
    dm.service.calendar = cal

    assert resolve_latest_completed_trading_date(dm) == "20250520"


def test_resolve_backtest_end_date_uses_settings_when_earlier():
    view = StrategySettingsView({"sampling": {"end_date": "20250101"}})

    result = resolve_backtest_end_date(
        settings_view=view,
        latest_completed_trading_date="20250520",
    )

    assert result.date == "20250101"
    assert result.source == SOURCE_SETTINGS


def test_resolve_backtest_end_date_caps_when_settings_later_than_latest():
    view = StrategySettingsView({"sampling": {"end_date": "20251231"}})

    result = resolve_backtest_end_date(
        settings_view=view,
        latest_completed_trading_date="20250520",
    )

    assert result.date == "20250520"
    assert result.source == SOURCE_LATEST_TRADING_DAY


def test_resolve_backtest_end_date_falls_back_to_latest():
    view = StrategySettingsView({"sampling": {}})

    result = resolve_backtest_end_date(
        settings_view=view,
        latest_completed_trading_date="20250520",
    )

    assert result.date == "20250520"
    assert result.source == SOURCE_LATEST_TRADING_DAY
