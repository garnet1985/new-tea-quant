#!/usr/bin/env python3
"""枚举产物买入字段校验与事件流。"""

from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity
from core.modules.strategy.services.data.output.event import (
    parse_opportunity_buy_fill,
)


class TestParseOpportunityBuyFill:
    def test_valid_fill(self):
        assert parse_opportunity_buy_fill(
            {"buy_date": "20240102", "buy_price": 10.5}
        ) == ("20240102", 10.5)

    def test_rejects_trigger_fallback(self):
        assert (
            parse_opportunity_buy_fill(
                {
                    "trigger_date": "20240101",
                    "trigger_price": 9.0,
                    "buy_date": "",
                    "buy_price": 0,
                }
            )
            is None
        )

    def test_scan_opportunity_does_not_copy_trigger_to_buy(self):
        opp = Opportunity(
            stock={},
            record_of_today={"date": "20240101", "close": 9.5},
        )
        assert opp.trigger_date == "20240101"
        assert opp.trigger_price == 9.5
        assert opp.buy_price == 0.0
        assert opp.buy_date == ""

    def test_pending_opportunity_not_serializable_as_fill(self):
        opp = Opportunity(
            stock={},
            record_of_today={"date": "20240101", "close": 9.5},
            trigger_date="20240101",
            trigger_price=9.5,
            buy_fill_pending=True,
        )
        d = opp.to_dict()
        assert parse_opportunity_buy_fill(d) is None

    def test_cost_basis_uses_buy_price_only(self):
        opp = Opportunity(
            stock={},
            record_of_today={},
            trigger_price=8.0,
            buy_price=10.0,
        )
        assert opp._cost_basis() == 10.0
