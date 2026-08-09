"""API contract tests for modules.market_profile Facade（对齐 API.md）。"""

from __future__ import annotations

import unittest

import pytest

from core.modules.market_profile import MarketRulesProxy
from core.modules.market_profile.contracts import LotSizeResolved, MarketBaseRules

pytestmark = pytest.mark.force_run


class TestMarketProfileApi(unittest.TestCase):
    def test_facade_export(self) -> None:
        import core.modules.market_profile as pkg

        self.assertEqual(pkg.__all__, ["MarketRulesProxy"])
        self.assertFalse(hasattr(pkg, "get_market_profile"))
        self.assertFalse(hasattr(pkg, "create_market_rules"))

    def test_for_market_and_available_ids(self) -> None:
        ids = MarketRulesProxy.available_ids()
        self.assertIn("china_a_stock", ids)
        self.assertIn("us_stock", ids)
        rules = MarketRulesProxy.for_market("china_a_stock")
        self.assertIsInstance(rules, MarketBaseRules)
        self.assertEqual(rules.profile_id, "china_a_stock")
        with self.assertRaises(ValueError):
            MarketRulesProxy.for_market("not_a_market")

    def test_proxy_methods(self) -> None:
        proxy = MarketRulesProxy()
        self.assertIn("china_a_stock", proxy.list_available())
        self.assertTrue(proxy.is_available("china_a_stock"))
        self.assertIsInstance(proxy.current, MarketBaseRules)
        self.assertEqual(proxy.get_market_id(), "china_a_stock")
        # 同 Proxy 内缓存
        self.assertIs(proxy.get_market("china_a_stock"), proxy.current)
        proxy.set_market("us_stock")
        self.assertEqual(proxy.get_market_id(), "us_stock")
        with self.assertRaises(ValueError):
            proxy.set_market("not_a_market")

    def test_lazy_load_does_not_precreate_all(self) -> None:
        proxy = MarketRulesProxy(default_market="china_a_stock")
        self.assertEqual(set(proxy._instances.keys()), {"china_a_stock"})
        proxy.get_market("hong_kong")
        self.assertEqual(set(proxy._instances.keys()), {"china_a_stock", "hong_kong"})

    def test_rules_core_methods(self) -> None:
        rules = MarketRulesProxy.for_market("china_a_stock")
        self.assertIsInstance(rules.get_limit_ratio(), float)
        up, down = rules.compute_limit_prices(10.0)
        self.assertIsInstance(up, float)
        self.assertIsInstance(down, float)
        self.assertTrue(rules.is_at_limit_up(11.0, 10.0, "600000.SH"))
        self.assertFalse(rules.is_at_limit_up(10.5, 10.0, "600000.SH"))
        lot = rules.resolve_lot_size("000001.SZ")
        self.assertIsInstance(lot, LotSizeResolved)
        self.assertEqual(lot.min_lot, 100)
        self.assertEqual(rules.floor_quantity_for_stock(150, "000001.SZ"), 100)
        self.assertEqual(rules.get_settlement_period(), 1)
        self.assertFalse(rules.is_allowed_to_sell(0))
        self.assertTrue(rules.is_allowed_to_sell(1))

    def test_contracts_symbols(self) -> None:
        self.assertTrue(MarketBaseRules is not None)
        self.assertTrue(LotSizeResolved is not None)


if __name__ == "__main__":
    unittest.main()
