#!/usr/bin/env python3
"""Opportunity.bind_scan_context 单元测试。"""

from __future__ import annotations

import unittest

from core.modules.strategy.core.engines.shared.data_class import Opportunity
from core.modules.strategy.core.engines.shared.services.strategy_settings import StrategySettings


class TestOpportunityBindScanContext(unittest.TestCase):
    def test_bind_scan_context(self) -> None:
        opp = Opportunity(stock={}, record_of_today={"close": 10.0})
        opp.bind_scan_context(
            strategy_name="demo",
            stock_id="600000.SH",
            stock_info={"id": "600000.SH", "name": "浦发银行"},
            trigger_date="20240102",
            trigger_price=10.0,
            opportunity_index=1,
        )
        self.assertEqual(opp.trigger_price, 10.0)
        self.assertEqual(opp.trigger_date, "20240102")
        self.assertEqual(opp.stock.id, "600000.SH")
        self.assertEqual(opp.meta.opportunity_id, "1")

    def test_bind_scan_context_sets_market_profile(self) -> None:
        opp = Opportunity(stock={}, record_of_today={"close": 10.0})
        opp.bind_scan_context(
            strategy_name="demo",
            stock_id="600000.SH",
            trigger_date="20240102",
            trigger_price=10.0,
            market_profile="china_a_stock",
        )
        self.assertEqual(opp.market_profile, "china_a_stock")

    def test_goal_exit_ratio_from_settings(self) -> None:
        settings = StrategySettings(
            raw_settings={
                "goal": {
                    "take_profit": {
                        "stages": [{"ratio": 0.2, "sell_ratio": 0.5}],
                    },
                },
            }
        )
        stage = settings.goal.take_profit
        assert stage is not None
        self.assertEqual(stage.exit_ratio, 0.5)
        self.assertFalse(stage.close_invest)


if __name__ == "__main__":
    unittest.main()
