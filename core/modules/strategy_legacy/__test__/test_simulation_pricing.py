#!/usr/bin/env python3
"""simulation_pricing 单元测试。"""

from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
    MonitorPriceModel,
    TradePriceModel,
)
from core.modules.strategy.engines.shared.helpers.simulation_pricing import (
    apply_buy_slippage,
    apply_sell_slippage,
    monitor_bar_price,
    trade_price_defers_to_next_session,
    trade_theoretical_price_on_bar,
    trade_theoretical_price_same_day,
)

_BAR = {"date": "20240102", "open": 10.0, "close": 10.5, "high": 11.0, "low": 9.5}


class TestSimulationPricing:
    def test_monitor_close(self):
        assert monitor_bar_price(_BAR, MonitorPriceModel.CLOSE) == 10.5

    def test_monitor_extreme(self):
        assert monitor_bar_price(_BAR, MonitorPriceModel.EXTREME) == 10.25

    def test_next_open_defers(self):
        assert trade_price_defers_to_next_session(TradePriceModel.NEXT_OPEN) is True
        assert trade_price_defers_to_next_session(TradePriceModel.CLOSE) is False

    def test_trade_on_bar_next_open_uses_open(self):
        px = trade_theoretical_price_on_bar(
            TradePriceModel.NEXT_OPEN, side="buy", bar=_BAR
        )
        assert px == 10.0

    def test_same_day_close(self):
        px = trade_theoretical_price_same_day(
            TradePriceModel.CLOSE, side="buy", bar=_BAR
        )
        assert px == 10.5

    def test_same_day_next_open_skip_at_edge(self):
        assert (
            trade_theoretical_price_same_day(
                TradePriceModel.NEXT_OPEN,
                side="buy",
                bar=_BAR,
                no_next_bar="skip_trade",
            )
            is None
        )

    def test_slippage(self):
        assert apply_buy_slippage(100.0, 10.0) == 100.1
        assert apply_sell_slippage(100.0, 10.0) == 99.9
