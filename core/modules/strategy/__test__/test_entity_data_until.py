#!/usr/bin/env python3
"""EntityDataLoader.data_until：DataKey cursor → hook keys (data_key.value)."""
from __future__ import annotations

import sys
import unittest
from typing import Any, Dict

try:
    import pandas as _pandas  # noqa: F401
except ImportError:
    import types

    sys.modules["pandas"] = types.ModuleType("pandas")

from core.modules.data_contract import DataContracts
from core.modules.data_contract.contracts import DataKey
from core.modules.data_contract.core.cache.default_store import reset_shared_contract_cache
from core.modules.strategy.core.services.data.entity_data import EntityDataLoader

_BASE_KLINE_KEY = "stock.kline.daily"


def _minimal_settings() -> Dict[str, Any]:
    return {
        "data": {
            "base": {
                "data_key": _BASE_KLINE_KEY,
                "params": {"adjust": "qfq"},
            },
            "required": [
                {"data_key": "macro.lpr", "params": {}},
            ],
            "min_required_records": 2,
        },
    }


class TestEntityDataUntilSlots(unittest.TestCase):
    def setUp(self) -> None:
        reset_shared_contract_cache()

    def tearDown(self) -> None:
        reset_shared_contract_cache()

    def test_data_until_uses_data_key_strings(self) -> None:
        dcm = DataContracts(cache_enabled=False)
        kline = dcm.issue(
            DataKey.STOCK_KLINE_DAILY,
            entity_id="600000.SH",
            should_load_initially=False,
        ).require_one()
        kline.data = [
            {"date": "20240101", "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0},
            {"date": "20240110", "open": 2.0, "high": 2.0, "low": 2.0, "close": 2.0},
        ]
        macro = dcm.issue(DataKey.MACRO_LPR, should_load_initially=False).require_contract()
        macro.data = [
            {"date": "20240101", "value": 3.0},
            {"date": "20240105", "value": 3.1},
        ]

        loader = EntityDataLoader(
            stock_id="600000.SH",
            settings=_minimal_settings(),
        )
        loader._apply_contracts_to_slots(
            {
                DataKey.STOCK_KLINE_DAILY: kline,
                DataKey.MACRO_LPR: macro,
            },
            start_date="20240101",
            end_date="20240131",
        )
        loader._rebuild_cursor()

        early = loader.data_until("20240104")
        self.assertEqual(len(early[_BASE_KLINE_KEY]), 1)
        self.assertEqual(len(early["macro.lpr"]), 1)

        data = loader.data_until("20240110")
        self.assertIn(_BASE_KLINE_KEY, data)
        self.assertIn("macro.lpr", data)
        self.assertNotIn("klines", data)
        self.assertEqual(len(data[_BASE_KLINE_KEY]), 2)
        self.assertEqual(data[_BASE_KLINE_KEY][-1]["date"], "20240110")
        self.assertEqual(len(data["macro.lpr"]), 2)


if __name__ == "__main__":
    unittest.main()
