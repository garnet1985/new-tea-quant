#!/usr/bin/env python3
"""策略 contract 注入路径的 K 线 slot 形状（klines → 标准 OHLC）。"""
import unittest

from core.modules.data_contract.contracts import DataKey
from core.modules.data_contract import DataContracts
from core.modules.data_contract.contracts import ContractCacheManager
from core.modules.strategy.services.data.injection.service import StrategyDataInjectionService
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)

_DEMO_STOCK = "000019.SZ"
_DEMO_START = "20250102"
_DEMO_END = "20250110"


class TestKlineSlotShape(unittest.TestCase):
    def test_stock_kline_loader_returns_standard_ohlc(self):
        dcm = DataContracts(contract_cache=ContractCacheManager())
        contract = dcm.issue(
            DataKey.STOCK_KLINE_DAILY,
            entity_id=_DEMO_STOCK,
            start=_DEMO_START,
            end=_DEMO_END,
            adjust="qfq",
        ).require_contract()
        contract.load(start=_DEMO_START, end=_DEMO_END)
        self.assertTrue(contract.data)
        row = contract.data[0]
        self.assertIn("high", row)
        self.assertIn("low", row)
        self.assertNotIn("qfq_open", row)
        self.assertNotIn("highest", row)

    def test_injection_service_klines_slot_matches_contract(self):
        view = StrategySettingsView.from_dict({
            "data": {
                "base_required_data": {
                    "data_id": "stock.kline.daily",
                    "params": {"adjust": "qfq"},
                    "indicators": {},
                },
            }
        })
        svc = StrategyDataInjectionService(
            _DEMO_STOCK,
            view,
            contract_cache=ContractCacheManager(),
        )
        svc.hydrate_row_slots(_DEMO_START, _DEMO_END, fresh_strategy_cache=True)
        klines = svc.get_klines()
        self.assertTrue(klines)
        row = klines[0]
        self.assertIn("open", row)
        self.assertIn("close", row)
        self.assertIn("high", row)
        self.assertIn("low", row)
        self.assertNotIn("qfq_close", row)

    def test_daily_base_and_weekly_extra_use_distinct_slots(self):
        view = StrategySettingsView.from_dict({
            "data": {
                "base_required_data": {
                    "data_id": "stock.kline.daily",
                    "params": {"adjust": "qfq"},
                },
                "extra_required_data_sources": [
                    {
                        "data_id": "stock.kline.weekly",
                        "params": {"adjust": "qfq"},
                        "indicators": {},
                    },
                ],
                "indicators": {},
            }
        })
        svc = StrategyDataInjectionService(
            _DEMO_STOCK,
            view,
            contract_cache=ContractCacheManager(),
        )
        svc.hydrate_row_slots(_DEMO_START, "20250130", fresh_strategy_cache=True)
        loaded = svc.get_loaded_data()
        self.assertIn("klines", loaded)
        self.assertIn("stock.kline.weekly", loaded)
        self.assertIsNot(loaded["klines"], loaded["stock.kline.weekly"])


if __name__ == "__main__":
    unittest.main()
