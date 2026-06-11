#!/usr/bin/env python3
import unittest

from core.modules.data_manager.data_manager import DataManager
from core.modules.data_manager.data_services.stock.sub_services.kline_service import (
    KlineService,
)


class TestKlineLoadOutput(unittest.TestCase):
    def test_load_qfq_uses_standard_ohlc_keys(self):
        dm = DataManager()
        rows = dm.service.stock.kline.load_qfq_split(
            "000019.SZ",
            term="daily",
            start_date="20230601",
            end_date="20230605",
        )
        self.assertTrue(rows)
        row = rows[0]
        self.assertIn("open", row)
        self.assertIn("close", row)
        self.assertIn("high", row)
        self.assertIn("low", row)
        self.assertNotIn("qfq_open", row)
        self.assertNotIn("qfq_close", row)

    def test_load_raw_matches_db_ohlc(self):
        dm = DataManager()
        svc = dm.service.stock.kline
        raw = svc.load_raw("000019.SZ", "daily", "20230601", "20230601")
        qfq = svc.load_qfq_split("000019.SZ", "daily", "20230601", "20230601")
        self.assertEqual(len(raw), 1)
        self.assertEqual(len(qfq), 1)
        self.assertNotEqual(raw[0]["close"], qfq[0]["close"])

    def test_global_offset_resolves_from_latest_anchor(self):
        events = [
            {
                "event_date": "20220721",
                "factor": 1.0216,
                "qfq_anchor": 4.23,
                "raw_anchor": 4.6,
            },
            {
                "event_date": "20250722",
                "factor": 1.1581,
                "qfq_anchor": 2.51,
                "raw_anchor": 2.56,
            },
        ]
        ctx = KlineService._resolve_global_qfq_context(events, factor_latest=1.1581)
        self.assertTrue(ctx["use_global_offset"])
        self.assertAlmostEqual(ctx["global_offset"], -0.05, places=4)

    def test_001227_ex_date_window_not_inflated(self):
        """兰州银行除权前不应再出现 ~2.70 的系统性偏高。"""
        dm = DataManager()
        rows = {
            r["date"]: r
            for r in dm.service.stock.kline.load_qfq_split(
                "001227.SZ", "daily", "20230529", "20230605"
            )
        }
        self.assertLess(rows["20230531"]["close"], 2.6)
        self.assertGreater(rows["20230531"]["close"], 2.4)


if __name__ == "__main__":
    unittest.main()
