#!/usr/bin/env python3
"""Tag stage 与真实 K 线加载的 OHLC 契约（high/low，无 qfq_* 宽列）。"""
import unittest

from core.modules.data_manager.data_manager import DataManager
from core.modules.data_contract.contract_const import DataKey
from core.modules.tag.components.job_staging.tag_batch_stage import stage_entities_batch


class TestTagKlineIntegration(unittest.TestCase):
    def test_batch_stage_klines_use_standard_ohlc(self):
        dm = DataManager()
        out = stage_entities_batch(
            data_mgr=dm,
            entities=[
                {
                    "entity_id": "000019.SZ",
                    "start_date": "20230601",
                    "end_date": "20230610",
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
        rows = out["000019.SZ"]["slot_data"][DataKey.STOCK_KLINE_DAILY.value]
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
