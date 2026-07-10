#!/usr/bin/env python3
"""OpportunityEnricher 单元测试。"""

from __future__ import annotations

import unittest

from core.modules.strategy.core.engines.shared.data_class import Opportunity
from core.modules.strategy.core.helpers.opportunity_enrichment import OpportunityEnricher


class TestOpportunityEnricher(unittest.TestCase):
    def test_goal_prices_from_settings(self) -> None:
        opp = Opportunity(stock={}, record_of_today={"close": 10.0})
        settings = {
            "goal": {
                "stop_loss": {"stages": [{"ratio": -0.2, "close_invest": True}]},
                "take_profit": {"stages": [{"ratio": 0.2, "close_invest": True}]},
            },
        }
        OpportunityEnricher.apply_trigger_fields(
            opp,
            settings=settings,
            strategy_name="demo",
            stock_id="600000.SH",
            stock_info={"id": "600000.SH", "name": "浦发银行"},
            trigger_date="20240102",
            trigger_price=10.0,
            opportunity_index=1,
        )
        self.assertEqual(opp.stop_loss_price, 8.0)
        self.assertEqual(opp.target_sell_price, 12.0)
        self.assertEqual(opp.buy_price, 10.0)
        self.assertEqual(opp.stock_id, "600000.SH")


if __name__ == "__main__":
    unittest.main()
