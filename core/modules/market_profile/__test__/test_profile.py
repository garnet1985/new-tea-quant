#!/usr/bin/env python3
import pytest

from core.infra.project_context import DiscoveryManager, merge_market_profile_dicts
from core.modules.market_profile import (
    MARKETS_CONFIG_DIR,
    clear_market_profile_cache,
    get_market_profile,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_market_profile_cache()
    yield
    clear_market_profile_cache()


class TestMarketProfile:
    def test_china_a_stock_from_merged_raw(self):
        raw = DiscoveryManager.load_overridable_config(
            MARKETS_CONFIG_DIR,
            "china_a_stock",
            merge_fn=merge_market_profile_dicts,
        )
        profile = get_market_profile("china_a_stock")
        assert profile.name == raw["name"]
        assert profile.resolve_limit_ratio("600519.SH") == 0.1
        assert profile.resolve_limit_ratio("300750.SZ") == 0.2
        assert profile.resolve_limit_ratio("688981.SH") == 0.2

    def test_limit_prices_main_board(self):
        profile = get_market_profile("china_a_stock")
        up, down = profile.compute_limit_prices("600519.SH", 10.0)
        assert up == 11.0
        assert down == 9.0

    def test_limit_prices_main_board_st_risk(self):
        profile = get_market_profile("china_a_stock")
        up, down = profile.compute_limit_prices("600519.SH", 10.0, ["st"])
        assert up == 10.5
        assert down == 9.5

    def test_limit_prices_ke_chuang_st_unchanged(self):
        profile = get_market_profile("china_a_stock")
        up, down = profile.compute_limit_prices("688981.SH", 10.0, ["star_st"])
        assert up == 12.0
        assert down == 8.0

    def test_resolve_limit_ratio_star_st_over_st(self):
        profile = get_market_profile("china_a_stock")
        assert profile.resolve_limit_ratio("600519.SH", ["st", "star_st"]) == 0.05

    def test_lot_size(self):
        profile = get_market_profile("china_a_stock")
        main = profile.resolve_lot_rules("000001.SZ")
        assert main.min_lot == 100
        assert main.lot_step == 100
        star = profile.resolve_lot_rules("688981.SH")
        assert star.min_lot == 200
        assert star.lot_step == 1

    def test_floor_buy_quantity(self):
        profile = get_market_profile("china_a_stock")
        assert profile.floor_buy_quantity(150, "000001.SZ") == 100
        assert profile.floor_buy_quantity(50, "000001.SZ") == 0
        assert profile.floor_buy_quantity(250, "688981.SH") == 250

    def test_cache_same_instance(self):
        a = get_market_profile("china_a_stock")
        b = get_market_profile("china_a_stock")
        assert a is b
