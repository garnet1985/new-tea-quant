#!/usr/bin/env python3
from core.modules.market_profile import clear_market_profile_cache, get_market_profile
from core.modules.strategy.engines.scanner.helpers.tradability import (
    _bars_for_scan_date,
    annotate_scan_opportunity,
)
from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity


def setup_function():
    clear_market_profile_cache()


def teardown_function():
    clear_market_profile_cache()


def test_bars_for_scan_date():
    klines = [
        {"date": "20240101", "close": 10.0},
        {"date": "20240102", "close": 11.0},
    ]
    signal, prev = _bars_for_scan_date(klines, "20240102")
    assert signal["date"] == "20240102"
    assert prev["date"] == "20240101"


def test_annotate_scan_sets_hint_when_limit_up():
    profile = get_market_profile("china_a_stock")
    limit_up, _ = profile.compute_limit_prices("000001.SZ", 10.0)
    opp = Opportunity(
        stock={"id": "000001.SZ"},
        record_of_today={},
        trigger_date="20240102",
        trigger_price=limit_up,
    )
    klines = [
        {"date": "20240101", "close": 10.0},
        {"date": "20240102", "close": limit_up},
    ]
    annotate_scan_opportunity(
        opp,
        settings_dict={"market_profile": "china_a_stock"},
        klines=klines,
        scan_date="20240102",
    )
    assert opp.buy_at_limit_up is True
    assert opp.metadata.get("tradability_hint") == "涨停附近，可能难以买入"
