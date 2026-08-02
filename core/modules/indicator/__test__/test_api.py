"""API contract tests for modules.indicator Facade."""

from __future__ import annotations

import unittest

import pytest

from core.modules.indicator import Indicator
from core.modules.indicator.contracts import BatchIndicatorResult

pytestmark = pytest.mark.force_run


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
            "list_indicators",
            "get_indicator_help",
            "warmup",
        ):
            self.assertTrue(callable(getattr(Indicator, name)))

    def test_contracts_symbol(self) -> None:
        self.assertTrue(BatchIndicatorResult is not None)


if __name__ == "__main__":
    unittest.main()
