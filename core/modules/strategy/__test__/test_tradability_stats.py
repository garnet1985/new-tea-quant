#!/usr/bin/env python3
from core.modules.strategy.engines.shared.helpers.tradability_stats import (
    count_tradability_in_opportunities,
    tradability_ratios,
)


def test_count_tradability_in_opportunities():
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
    counts = count_tradability_in_opportunities(rows)
    assert counts["buy_tradability_sample_count"] == 2
    assert counts["buy_at_limit_up_count"] == 1
    assert counts["sell_tradability_sample_count"] == 2
    assert counts["sell_at_limit_down_count"] == 1
    ratios = tradability_ratios(counts)
    assert ratios["limit_up_buy_ratio"] == 50.0
    assert ratios["limit_down_sell_ratio"] == 50.0
