#!/usr/bin/env python3
import unittest

from core.modules.strategy.launcher.workbench_stock_detail import (
    _build_price_markers,
    _is_price_target_win,
)


class TestWorkbenchStockDetailPriceMarkers(unittest.TestCase):
    def test_is_price_target_win_from_profit(self):
        self.assertTrue(_is_price_target_win({"weighted_profit": 120.5}))
        self.assertFalse(_is_price_target_win({"weighted_profit": -10}))
        self.assertTrue(_is_price_target_win({"profit": 1.0}))
        self.assertFalse(_is_price_target_win({"target_type": "stop_loss"}))

    def test_build_price_markers_buy_and_targets(self):
        investments = [
            {
                "opportunity_id": "opp-1",
                "trigger_date": "20230102",
                "buy_date": "20230103",
                "buy_price": 10.0,
                "status": "win",
                "completed_targets": [
                    {
                        "name": "take_profit_1",
                        "target_type": "take_profit",
                        "sell_date": "20230110",
                        "sell_price": 11.0,
                        "weighted_profit": 100.0,
                        "profit_ratio": 0.1,
                    },
                    {
                        "name": "stop_loss_1",
                        "target_type": "stop_loss",
                        "sell_date": "20230115",
                        "sell_price": 9.0,
                        "weighted_profit": -50.0,
                        "profit_ratio": -0.05,
                    },
                ],
            },
        ]
        by_date = {
            "20230102": {"date": "20230102", "open": 9.8, "close": 10.0, "high": 10.1, "low": 9.7},
            "20230103": {"date": "20230103", "open": 10, "close": 10.2, "high": 10.5, "low": 9.8},
            "20230110": {"date": "20230110", "open": 11, "close": 11.1, "high": 11.3, "low": 10.8},
            "20230115": {"date": "20230115", "open": 9, "close": 9.1, "high": 9.2, "low": 8.9},
        }
        markers = _build_price_markers(investments, by_date)
        self.assertEqual(len(markers), 3)
        self.assertEqual(markers[0]["type"], "buy")
        self.assertEqual(markers[0]["label"], "买入")
        self.assertEqual(markers[0]["date"], "20230103")
        self.assertEqual(markers[0]["detail"].get("trigger_date"), "20230102")


if __name__ == "__main__":
    unittest.main()
