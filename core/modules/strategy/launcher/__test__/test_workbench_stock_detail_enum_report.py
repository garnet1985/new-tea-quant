#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path

from core.modules.strategy.launcher.workbench_stock_detail import (
    _build_stock_enum_report_metrics,
)


class TestWorkbenchStockDetailEnumReport(unittest.TestCase):
    def test_build_stock_enum_report_metrics_single_stock(self):
        opportunities = [
            {
                "trigger_date": "20230103",
                "sell_date": "20230110",
                "status": "win",
                "buy_date": "20230104",
                "buy_price": "10.0",
                "buy_at_limit_up": "false",
            },
            {
                "trigger_date": "20230201",
                "sell_date": "20230208",
                "status": "loss",
                "buy_date": "20230202",
                "buy_price": "11.0",
                "buy_at_limit_up": "true",
            },
            {
                "trigger_date": "20230301",
                "sell_date": "20230308",
                "status": "open",
                "buy_date": "20230302",
                "buy_price": "12.0",
            },
            {
                "trigger_date": "20230401",
                "sell_date": "20230408",
                "status": "win",
                "sell_reason": "enumeration_end",
                "buy_date": "20230402",
                "buy_price": "12.0",
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            metrics = _build_stock_enum_report_metrics(
                "600000.SH",
                opportunities,
                Path(tmp),
            )
        self.assertEqual(metrics.get("totalOpportunities"), 4)
        self.assertEqual(metrics.get("totalStocks"), 1)
        self.assertEqual(metrics.get("winCount"), 1)
        self.assertEqual(metrics.get("lossCount"), 1)
        self.assertEqual(metrics.get("winRateSampleCount"), 2)
        self.assertEqual(metrics.get("winRate"), 50.0)
        self.assertEqual(metrics.get("buyAtLimitUpCount"), 1)
        self.assertEqual(metrics.get("buyTradabilitySampleCount"), 2)
        self.assertEqual(metrics.get("limitUpBuyRatio"), 50.0)
        self.assertGreater(metrics.get("meanDuration", 0), 0)


if __name__ == "__main__":
    unittest.main()
