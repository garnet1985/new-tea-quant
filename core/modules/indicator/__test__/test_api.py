"""API contract tests for modules.indicator Facade（对齐 API.md）。"""

from __future__ import annotations

import unittest

import pytest

from core.modules.indicator import Indicator
from core.modules.indicator.contracts import BatchIndicatorResult

pytestmark = pytest.mark.force_run


def _ohlcv(n: int = 60) -> list[dict]:
    return [
        {
            "date": f"2024{i:04d}",
            "open": 10 + i * 0.1,
            "high": 10.5 + i * 0.1,
            "low": 9.5 + i * 0.1,
            "close": 10 + i * 0.1,
            "volume": 1000 + i,
        }
        for i in range(n)
    ]


class TestIndicatorApi(unittest.TestCase):
    def test_facade_export(self) -> None:
        import core.modules.indicator as pkg

        self.assertEqual(pkg.__all__, ["Indicator"])
        self.assertFalse(hasattr(pkg, "IndicatorService"))
        self.assertFalse(hasattr(pkg, "BatchIndicatorResult"))

    def test_public_methods(self) -> None:
        for name in (
            "calculate",
            "compute",
            "compute_batch",
            "ma",
            "ema",
            "rsi",
            "macd",
            "bbands",
            "atr",
            "stoch",
            "adx",
            "obv",
            "list_indicators",
            "get_indicator_help",
            "warmup",
        ):
            self.assertTrue(callable(getattr(Indicator, name)), name)

    def test_contracts_symbol(self) -> None:
        self.assertTrue(BatchIndicatorResult is not None)

    def test_warmup_and_list_indicators(self) -> None:
        Indicator.warmup()
        names = Indicator.list_indicators()
        self.assertIsInstance(names, list)
        self.assertGreater(len(names), 10)
        self.assertIn("sma", names)

    def test_ma_rsi_smoke(self) -> None:
        klines = _ohlcv()
        ma = Indicator.ma(klines, length=5)
        rsi = Indicator.rsi(klines, length=14)
        self.assertIsInstance(ma, list)
        self.assertEqual(len(ma), len(klines))
        self.assertIsInstance(rsi, list)
        self.assertAlmostEqual(ma[-1], sum(r["close"] for r in klines[-5:]) / 5, places=5)

    def test_stoch_adx_obv_smoke(self) -> None:
        klines = _ohlcv()
        stoch = Indicator.stoch(klines, k=14, d=3, smooth_k=3)
        adx = Indicator.adx(klines, length=14)
        obv = Indicator.obv(klines)
        self.assertIsInstance(stoch, dict)
        self.assertGreaterEqual(len(stoch), 1)
        self.assertIsInstance(adx, dict)
        self.assertTrue(any(k.startswith("ADX") for k in adx))
        self.assertIsInstance(obv, list)
        self.assertEqual(len(obv), len(klines))

    def test_compute_batch_shape(self) -> None:
        klines = _ohlcv()
        rows = Indicator.compute_batch(
            klines,
            {"rsi": [{"length": 14}], "sma": [{"length": 5}]},
        )
        self.assertEqual(len(rows), 2)
        for name, params, values in rows:
            self.assertIsInstance(name, str)
            self.assertIsInstance(params, dict)
            self.assertIsNotNone(values)


if __name__ == "__main__":
    unittest.main()
