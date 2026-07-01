#!/usr/bin/env python3
"""slice_based EntityHoldings 单元测试。"""

from __future__ import annotations

import unittest

from core.modules.strategy.core.engines.enumerator.slice_based.state.holdings import EntityHoldings
from core.modules.strategy.core.engines.shared.data_classes import Opportunity


class TestEntityHoldings(unittest.TestCase):
    def test_force_exit_closes_active(self) -> None:
        holdings = EntityHoldings()
        opp = Opportunity(
            stock={"id": "600000.SH"},
            record_of_today={"close": 10.0},
            trigger_date="20240102",
            trigger_price=10.0,
        )
        holdings.register_entry(opp)
        holdings.force_exit_all("20241231", 11.0, reason="period_end")
        self.assertEqual(len(holdings.active), 0)
        self.assertEqual(len(holdings.recorded), 1)
        self.assertEqual(holdings.recorded[0].sell_price, 11.0)
        self.assertEqual(holdings.recorded[0].outcome, "completed")
        self.assertEqual(holdings.recorded[0].sell_reason, "period_end")

    def test_close_expired_by_open_dates(self) -> None:
        holdings = EntityHoldings()
        opp = Opportunity(
            stock={"id": "600000.SH"},
            record_of_today={"close": 10.0},
            trigger_date="20240102",
            trigger_price=10.0,
        )
        holdings.register_entry(opp)
        open_dates = ["20240102", "20240103", "20240104"]
        holdings.close_expired(
            "20240104",
            10.5,
            max_holding_days=3,
            open_dates=open_dates,
        )
        self.assertEqual(len(holdings.active), 0)
        self.assertEqual(holdings.recorded[0].sell_reason, "max_holding")


if __name__ == "__main__":
    unittest.main()
