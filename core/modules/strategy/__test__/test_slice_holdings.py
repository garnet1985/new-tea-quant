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

    def test_close_goal_stop_loss(self) -> None:
        holdings = EntityHoldings()
        opp = Opportunity(
            stock={"id": "600000.SH"},
            record_of_today={"close": 10.0},
            trigger_date="20240102",
            trigger_price=10.0,
            stop_loss_price=9.0,
        )
        holdings.register_entry(opp)
        holdings.close_goal_targets({"open": 10.0, "high": 10.5, "low": 8.5, "close": 9.5})
        self.assertEqual(len(holdings.active), 0)
        self.assertEqual(holdings.recorded[0].sell_price, 9.0)
        self.assertEqual(holdings.recorded[0].sell_reason, "stop_loss")

    def test_close_goal_take_profit(self) -> None:
        holdings = EntityHoldings()
        opp = Opportunity(
            stock={"id": "600000.SH"},
            record_of_today={"close": 10.0},
            trigger_date="20240102",
            trigger_price=10.0,
            target_sell_price=12.0,
        )
        holdings.register_entry(opp)
        holdings.close_goal_targets({"open": 11.0, "high": 12.5, "low": 10.5, "close": 12.0})
        self.assertEqual(holdings.recorded[0].sell_reason, "take_profit")
        self.assertEqual(holdings.recorded[0].sell_price, 12.0)

    def test_register_entry_rejects_second_open(self) -> None:
        holdings = EntityHoldings()
        first = Opportunity(
            stock={"id": "600000.SH"},
            record_of_today={"close": 10.0},
            trigger_date="20240102",
            trigger_price=10.0,
        )
        holdings.register_entry(first)
        second = Opportunity(
            stock={"id": "600000.SH"},
            record_of_today={"close": 11.0},
            trigger_date="20240103",
            trigger_price=11.0,
        )
        with self.assertRaises(ValueError):
            holdings.register_entry(second)


if __name__ == "__main__":
    unittest.main()
