#!/usr/bin/env python3
"""交收规则用例。"""

from __future__ import annotations

import pytest

from core.modules.market_profile import MarketRulesProxy

pytestmark = pytest.mark.force_run


def test_china_a_stock_settlement_t_plus_one():
    rules = MarketRulesProxy(default_market="china_a_stock").current
    assert rules.get_settlement_period() == 1
    assert rules.is_allowed_to_sell(0) is False
    assert rules.is_allowed_to_sell(1) is True


def test_us_stock_settlement_t_plus_zero():
    rules = MarketRulesProxy(default_market="us_stock").current
    assert rules.get_settlement_period() == 0
    assert rules.is_allowed_to_sell(0) is True
