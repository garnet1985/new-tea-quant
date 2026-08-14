#!/usr/bin/env python3
"""Indicator compute / calculate 路径单测（实现细节，非公开 API 契约）。"""

from __future__ import annotations

import unittest

import pytest

from core.modules.indicator import Indicator

pytestmark = pytest.mark.force_run


class TestComputePaths(unittest.TestCase):
    def test_trim_klines_for_calculate_keeps_ochlv_only(self):
        rows = [
            {
                "date": "20240101",
                "open": 1.0,
                "high": 1.1,
                "low": 0.9,
                "close": 1.05,
                "volume": 100,
                "extra": "drop-me",
            }
        ]
        slim = Indicator._trim_klines_for_ohlcv(rows)
        self.assertEqual(set(slim[0].keys()), {"open", "high", "low", "close", "volume"})
        self.assertEqual(slim[0]["high"], 1.1)
        self.assertEqual(slim[0]["low"], 0.9)

    def test_compute_rsi_matches_rsi_helper(self):
        klines = [{"close": float(10 + i * 0.1)} for i in range(40)]
        a = Indicator.compute("rsi", klines, length=14)
        b = Indicator.rsi(klines, length=14)
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        self.assertEqual(len(a), len(b))
        self.assertAlmostEqual(a[-1], b[-1], places=5)
        self.assertAlmostEqual(a[-5], b[-5], places=5)

    def test_compute_ma_alias_uses_sma_close_path(self):
        klines = [{"close": float(i)} for i in range(30)]
        via_ma = Indicator.compute("ma", klines, length=5)
        via_sma = Indicator.compute("sma", klines, length=5)
        self.assertIsNotNone(via_ma)
        self.assertEqual(len(via_ma), len(via_sma))
        self.assertAlmostEqual(via_ma[-1], via_sma[-1], places=5)

    def test_calculate_uses_full_row_without_dropping_extra_columns(self):
        rows = [
            {
                "date": "20240101",
                "open": 1.0,
                "high": 1.1,
                "low": 0.9,
                "close": 1.0,
                "volume": 10,
                "marker": "keep-me",
            }
            for _ in range(25)
        ]
        slim = Indicator._trim_klines_for_ohlcv(rows)
        self.assertNotIn("marker", slim[0])
        # calculate fallback path reads full rows (layer 3); sma exists on ta
        out = Indicator.calculate("sma", rows, length=5)
        self.assertIsNotNone(out)

    def test_compute_unknown_ta_name_uses_trimmed_before_calculate(self):
        """pandas-ta 存在但未列入专通名单时，仍走 layer2 而非宽表 calculate。"""
        klines = [
            {
                "open": 10 + i * 0.1,
                "high": 10.5 + i * 0.1,
                "low": 9.5 + i * 0.1,
                "close": 10 + i * 0.1,
                "volume": 1000 + i,
            }
            for i in range(40)
        ]
        via_compute = Indicator.compute("cci", klines, length=14)
        via_layer2 = Indicator._ta_on_ohlcv("cci", klines, length=14)
        self.assertIsNotNone(via_compute)
        self.assertEqual(len(via_compute), len(via_layer2))
        self.assertAlmostEqual(via_compute[-1], via_layer2[-1], places=5)

    def test_compute_batch_matches_sequential_compute(self):
        klines = [
            {
                "open": 10 + i * 0.1,
                "high": 10.5 + i * 0.1,
                "low": 9.5 + i * 0.1,
                "close": 10 + i * 0.1,
                "volume": 1000 + i,
            }
            for i in range(60)
        ]
        cfg = {
            "rsi": [{"length": 14}],
            "sma": [{"length": 5}, {"length": 20}],
            "macd": [{"fast": 12, "slow": 26, "signal": 9}],
        }
        batch_rows = Indicator.compute_batch(klines, cfg)
        self.assertEqual(len(batch_rows), 4)

        for name, item_cfg, batch_result in batch_rows:
            single = Indicator.compute(name, klines, **item_cfg)
            self.assertIsNotNone(single)
            if isinstance(single, list):
                self.assertEqual(len(batch_result), len(single))
                self.assertAlmostEqual(batch_result[-1], single[-1], places=5)
            else:
                self.assertEqual(set(batch_result.keys()), set(single.keys()))

    def test_compute_macd_returns_dict(self):
        klines = [
            {
                "open": 10 + i * 0.1,
                "high": 10.5 + i * 0.1,
                "low": 9.5 + i * 0.1,
                "close": 10 + i * 0.1,
                "volume": 1000 + i,
            }
            for i in range(60)
        ]
        out = Indicator.compute("macd", klines, fast=12, slow=26, signal=9)
        self.assertIsInstance(out, dict)
        self.assertGreaterEqual(len(out), 2)


if __name__ == "__main__":
    unittest.main()
