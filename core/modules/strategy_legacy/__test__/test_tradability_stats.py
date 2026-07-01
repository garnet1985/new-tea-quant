#!/usr/bin/env python3
from core.modules.strategy.engines.shared.helpers.tradability_stats import (
    tradability_bundle_from_opportunities,
)


def test_tradability_bundle_from_opportunities():
    rows = [
        {
            "buy_date": "20240102",
            "buy_price": 10.0,
            "buy_at_limit_up": True,
            "completed_targets": [
                {"sell_at_limit_down": False},
                {"sell_at_limit_down": True},
            ],
        },
        {
            "buy_date": "20240201",
            "buy_price": 9.0,
            "buy_at_limit_up": False,
            "completed_targets": [],
        },
    ]
    bundle = tradability_bundle_from_opportunities(rows)
    assert bundle["buy_tradability_sample_count"] == 2
    assert bundle["buy_at_limit_up_count"] == 1
    assert bundle["sell_tradability_sample_count"] == 2
    assert bundle["sell_at_limit_down_count"] == 1
    assert bundle["limit_up_buy_ratio"] == 50.0
    assert bundle["limit_down_sell_ratio"] == 50.0
