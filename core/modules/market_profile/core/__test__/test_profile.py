#!/usr/bin/env python3
"""市场规则数值用例（走 MarketRulesProxy）。"""

from __future__ import annotations

import pytest

from core.modules.market_profile import MarketRulesProxy

pytestmark = pytest.mark.force_run


@pytest.fixture
def china():
    return MarketRulesProxy(default_market="china_a_stock").current


class TestMarketProfile:
    def test_limit_prices_main_board(self, china):
        up, down = china.compute_limit_prices_for_stock(10.0, "600519.SH")
        assert up == 11.0
        assert down == 9.0

    def test_limit_prices_main_board_st_risk(self, china):
        up, down = china.compute_limit_prices_for_stock(10.0, "600519.SH", ["st"])
        assert up == 10.5
        assert down == 9.5

    def test_limit_ratio_star(self, china):
        assert china.get_limit_ratio_for_stock("688981.SH") == 0.2

    def test_lot_size(self, china):
        main = china.resolve_lot_size("000001.SZ")
        assert main.min_lot == 100
        assert main.lot_step == 100
        star = china.resolve_lot_size("688981.SH")
        assert star.min_lot == 200
        assert star.lot_step == 1

    def test_floor_quantity(self, china):
        assert china.floor_quantity_for_stock(150, "000001.SZ") == 100
        assert china.floor_quantity_for_stock(50, "000001.SZ") == 0
        assert china.floor_quantity_for_stock(250, "688981.SH") == 250

    def test_same_proxy_market_instance(self):
        proxy = MarketRulesProxy()
        assert proxy.get_market("china_a_stock") is proxy.get_market("china_a_stock")
