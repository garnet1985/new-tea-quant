"""API contract tests for modules.market_profile Facade."""

from __future__ import annotations

import unittest

import pytest

from core.modules.market_profile import MarketRulesProxy
from core.modules.market_profile.contracts import MarketBaseRules

pytestmark = pytest.mark.force_run


class TestMarketProfileApi(unittest.TestCase):
    def test_facade_export(self) -> None:
        import core.modules.market_profile as pkg

        self.assertEqual(pkg.__all__, ["MarketRulesProxy"])
        self.assertFalse(hasattr(pkg, "get_market_profile"))

    def test_proxy_methods(self) -> None:
        proxy = MarketRulesProxy()
        self.assertIn("china_a_stock", proxy.list_available())
        self.assertTrue(proxy.is_available("china_a_stock"))
        self.assertIsInstance(proxy.current, MarketBaseRules)
        self.assertEqual(proxy.get_market_id(), "china_a_stock")
        proxy.set_market("us_stock")
        self.assertEqual(proxy.get_market_id(), "us_stock")
        with self.assertRaises(ValueError):
            proxy.set_market("not_a_market")

    def test_rules_core_methods(self) -> None:
        rules = MarketRulesProxy().current
        self.assertIsInstance(rules.get_limit_ratio(), float)
        up, down = rules.compute_limit_prices(10.0)
        self.assertIsInstance(up, float)
        self.assertIsInstance(down, float)
        self.assertIsInstance(rules.get_min_lot(), int)
        self.assertIsInstance(rules.get_settlement_period(), int)


if __name__ == "__main__":
    unittest.main()
