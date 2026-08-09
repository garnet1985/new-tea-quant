#!/usr/bin/env python3
import unittest

from core.modules.data_manager import DataManager
from core.modules.data_manager.core.data_services.stock.sub_services.kline_service import (
    KlineService,
)

# 与 setup/init_data/data_demo.zip 日期窗对齐（20250101–20260101）
_DEMO_STOCK = "000019.SZ"
_DEMO_START = "20250102"
_DEMO_END = "20250110"
_EX_STOCK = "001227.SZ"
_EX_WINDOW_START = "20250120"
_EX_WINDOW_END = "20250128"
_EX_CHECK_DATE = "20250123"


class TestKlineLoadOutput(unittest.TestCase):
    def test_load_qfq_uses_standard_ohlc_keys(self):
        dm = DataManager()
        rows = dm.service.stock.kline.load_qfq_split(
            _DEMO_STOCK,
            term="daily",
            start_date=_DEMO_START,
            end_date=_DEMO_END,
        )
        self.assertTrue(rows)
        row = rows[0]
        self.assertIn("open", row)
        self.assertIn("close", row)
        self.assertIn("high", row)
        self.assertIn("low", row)
        self.assertNotIn("qfq_open", row)
        self.assertNotIn("qfq_close", row)

    def test_load_qfq_embeds_raw_ohlc(self):
        dm = DataManager()
        svc = dm.service.stock.kline
        raw_rows = svc.load_raw(_DEMO_STOCK, "daily", _DEMO_START, _DEMO_START)
        qfq_rows = svc.load_qfq_split(_DEMO_STOCK, "daily", _DEMO_START, _DEMO_START)
        self.assertEqual(len(raw_rows), 1)
        self.assertEqual(len(qfq_rows), 1)
        qfq = qfq_rows[0]
        raw = raw_rows[0]
        self.assertIsInstance(qfq.get("raw"), dict)
        for field in ("open", "high", "low", "close"):
            self.assertEqual(qfq["raw"][field], raw[field])
        self.assertNotEqual(qfq["close"], qfq["raw"]["close"])

    def test_load_raw_matches_db_ohlc(self):
        dm = DataManager()
        svc = dm.service.stock.kline
        raw = svc.load_raw(_DEMO_STOCK, "daily", _DEMO_START, _DEMO_START)
        qfq = svc.load_qfq_split(_DEMO_STOCK, "daily", _DEMO_START, _DEMO_START)
        self.assertEqual(len(raw), 1)
        self.assertEqual(len(qfq), 1)
        self.assertNotEqual(raw[0]["close"], qfq[0]["close"])

    def test_apply_qfq_snapshots_raw_even_without_event(self):
        kline = {"date": "20250102", "open": 10.0, "high": 11.0, "low": 9.0, "close": 10.5}
        KlineService._apply_qfq_from_event_info(
            KlineService.__new__(KlineService),
            kline,
            {"event": None, "qfq_diff": 0.0, "is_adjusted": False},
            factor_latest=1.0,
        )
        self.assertEqual(
            kline["raw"],
            {"open": 10.0, "high": 11.0, "low": 9.0, "close": 10.5},
        )
        self.assertEqual(kline["close"], 10.5)

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
                _EX_STOCK, "daily", _EX_WINDOW_START, _EX_WINDOW_END
            )
        }
        self.assertLess(rows[_EX_CHECK_DATE]["close"], 2.6)
        self.assertGreater(rows[_EX_CHECK_DATE]["close"], 2.1)
        self.assertIn("raw", rows[_EX_CHECK_DATE])
        self.assertIn("close", rows[_EX_CHECK_DATE]["raw"])


if __name__ == "__main__":
    unittest.main()
