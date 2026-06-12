#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path

from core.modules.strategy.engines.simulator.price_factor.stock_ref import (
    build_price_stock_ref_entry,
    build_price_stock_ref_map,
    load_price_stock_ref_from_dir,
    write_price_stock_ref,
)


class TestPriceStockRef(unittest.TestCase):
    def test_build_price_stock_ref_entry(self):
        stock_summary = {
            "stock": {"id": "600000.SH"},
            "investments": [
                {
                    "stock_name": "浦发银行",
                    "status": "win",
                    "roi": 0.12,
                    "holding_days": 10,
                    "completed_targets": [
                        {"target_type": "take_profit", "name": "win_1"},
                    ],
                },
                {
                    "status": "loss",
                    "roi": -0.05,
                    "holding_days": 8,
                    "completed_targets": [
                        {"target_type": "expired", "name": "expiration"},
                    ],
                },
            ],
            "summary": {
                "total_investments": 2,
                "total_win": 1,
                "total_loss": 1,
                "avg_roi": 0.035,
                "avg_duration_in_days": 9.0,
            },
        }
        entry = build_price_stock_ref_entry(stock_summary)
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry["stock_name"], "浦发银行")
        self.assertEqual(entry["win_rate"], 50.0)
        self.assertEqual(entry["avg_roi"], 3.5)
        self.assertEqual(entry["avg_duration_in_days"], 9.0)
        self.assertEqual(entry["expiration_ratio"], 50.0)

    def test_write_and_load_price_stock_ref(self):
        summaries = [
            {
                "stock": {"id": "000001.SZ"},
                "investments": [{"status": "win", "roi": 0.1, "holding_days": 5}],
                "summary": {
                    "total_investments": 1,
                    "total_win": 1,
                    "avg_roi": 0.1,
                    "avg_duration_in_days": 5.0,
                },
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_price_stock_ref(root, summaries)
            loaded = load_price_stock_ref_from_dir(root)
            self.assertIn("000001.SZ", loaded)
            self.assertEqual(loaded["000001.SZ"]["win_rate"], 100.0)

    def test_build_price_stock_ref_map_skips_empty(self):
        out = build_price_stock_ref_map([{"stock": {"id": "600000.SH"}, "investments": []}])
        self.assertEqual(out, {})


if __name__ == "__main__":
    unittest.main()
