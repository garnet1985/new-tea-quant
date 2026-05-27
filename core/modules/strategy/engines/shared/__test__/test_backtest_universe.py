"""回测 PIT universe 与 env scope（stock_ids，无日历窗）。"""
from unittest.mock import MagicMock, patch

from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.shared.helpers.backtest_date_resolve import (
    BacktestDateRange,
    SOURCE_SETTINGS,
    resolve_backtest_universe,
)
def test_resolve_backtest_universe_single_pass_when_start_configured():
    list_svc = MagicMock()
    list_svc.load.return_value = [{"id": "000001.SZ"}]
    view = StrategySettingsView(
        {"sampling": {"start_date": "20240101", "end_date": "20241231"}}
    )

    period, universe = resolve_backtest_universe(
        list_svc=list_svc,
        settings_view=view,
        latest_completed_trading_date="20241231",
        data_manager=None,
    )

    assert period.start_date == "20240101"
    assert period.end_date == "20241231"
    assert len(universe) == 1
    list_svc.load.assert_called_once_with(
        period_start="20240101", period_end="20241231"
    )


@patch(
    "core.modules.strategy.engines.shared.helpers.backtest_date_resolve.resolve_backtest_date_range"
)
def test_resolve_backtest_universe_two_pass_reload(mock_range):
    mock_range.return_value = BacktestDateRange(
        "20240601",
        "20241231",
        SOURCE_SETTINGS,
        SOURCE_SETTINGS,
    )
    list_svc = MagicMock()
    list_svc.load.side_effect = [
        [{"id": "000001.SZ"}, {"id": "600000.SH"}],
        [{"id": "600000.SH"}],
    ]
    view = StrategySettingsView({"sampling": {"end_date": "20241231"}})

    period, universe = resolve_backtest_universe(
        list_svc=list_svc,
        settings_view=view,
        latest_completed_trading_date="20241231",
        data_manager=None,
    )

    assert period.start_date == "20240601"
    assert len(universe) == 1
    assert list_svc.load.call_count == 2
