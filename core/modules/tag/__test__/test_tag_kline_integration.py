#!/usr/bin/env python3
"""Tag stage 与真实 K 线加载的 OHLC 契约（high/low，无 qfq_* 宽列）。"""
import unittest

from core.modules.data_manager.data_manager import DataManager
from core.modules.data_contract.contract_const import DataKey
from core.modules.tag.engines.shared.staging.batch_stage import stage_entities_batch

_DEMO_STOCK = "000019.SZ"
_DEMO_START = "20250102"
_DEMO_END = "20250110"


class TestTagKlineIntegration(unittest.TestCase):
    def test_batch_stage_klines_use_standard_ohlc(self):
        dm = DataManager()
        out = stage_entities_batch(
            data_mgr=dm,
            entities=[
                {
                    "entity_id": _DEMO_STOCK,
                    "start_date": _DEMO_START,
                    "end_date": _DEMO_END,
                }
            ],
            settings={
                "data": {
                    "required": [
                        {
                            "data_id": DataKey.STOCK_KLINE_DAILY.value,
                            "params": {"adjust": "qfq"},
                        }
                    ]
                }
            },
            tag_definition_ids=[1],
        )
        rows = out[_DEMO_STOCK]["slot_data"][DataKey.STOCK_KLINE_DAILY.value]
        self.assertTrue(rows)
        row = rows[0]
        self.assertIn("open", row)
        self.assertIn("high", row)
        self.assertIn("low", row)
        self.assertIn("close", row)
        self.assertNotIn("qfq_open", row)
        self.assertNotIn("highest", row)


if __name__ == "__main__":
    unittest.main()
