#!/usr/bin/env python3
"""策略 contract 注入路径的 K 线 slot 形状（klines → 标准 OHLC）。"""
import unittest

from core.modules.data_contract.contract_const import DataKey
from core.modules.data_contract.data_contract_manager import DataContractManager
from core.modules.data_contract.cache import ContractCacheManager
from core.modules.strategy.services.data.injection.service import StrategyDataInjectionService
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)


class TestKlineSlotShape(unittest.TestCase):
    def test_stock_kline_loader_returns_standard_ohlc(self):
        dcm = DataContractManager(contract_cache=ContractCacheManager())
        contract = dcm.issue(
            DataKey.STOCK_KLINE,
            entity_id="000019.SZ",
            start="20230601",
            end="20230610",
            term="daily",
            adjust="qfq",
        ).require_contract()
        contract.load(start="20230601", end="20230610")
        self.assertTrue(contract.data)
        row = contract.data[0]
        self.assertIn("high", row)
        self.assertIn("low", row)
        self.assertNotIn("qfq_open", row)
        self.assertNotIn("highest", row)

    def test_injection_service_klines_slot_matches_contract(self):
        view = StrategySettingsView.from_dict({
            "data": {
                "base_required_data": {"params": {"term": "daily", "adjust": "qfq"}},
                "indicators": {},
            }
        })
        svc = StrategyDataInjectionService(
            "000019.SZ",
            view,
            contract_cache=ContractCacheManager(),
        )
        svc.hydrate_row_slots("20230601", "20230610", fresh_strategy_cache=True)
        klines = svc.get_klines()
        self.assertTrue(klines)
        row = klines[0]
        self.assertIn("open", row)
        self.assertIn("close", row)
        self.assertIn("high", row)
        self.assertIn("low", row)
        self.assertNotIn("qfq_close", row)


if __name__ == "__main__":
    unittest.main()
