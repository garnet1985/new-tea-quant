#!/usr/bin/env python3
"""BaseStrategyWorker scan 辅助方法单元测试。"""

from __future__ import annotations

import unittest
from typing import Any, Dict, Optional

from core.modules.strategy.base_strategy_worker import BaseStrategyWorker
from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.types import (
    CalendarAsOfContext,
)


class _HelperProbeWorker(BaseStrategyWorker):
    def scan_opportunity(
        self, data: Dict[str, Any], settings: Dict[str, Any]
    ) -> Optional[Opportunity]:
        return None


class TestWorkerScanHelpers(unittest.TestCase):
    def test_get_record_of_today_empty(self):
        self.assertIsNone(BaseStrategyWorker.get_record_of_today({}))
        self.assertIsNone(BaseStrategyWorker.get_record_of_today({"klines": []}))

    def test_get_record_of_today_latest(self):
        data = {"klines": [{"date": "20240101"}, {"date": "20240102"}]}
        self.assertEqual(BaseStrategyWorker.get_record_of_today(data), {"date": "20240102"})

    def test_signal_date(self):
        record_of_today = {"date": "20240614"}
        self.assertEqual(BaseStrategyWorker.signal_date(record_of_today), "20240614")

    def test_core_int_and_float(self):
        settings = {"core": {"seed": "42", "entry_probability": "0.06"}}
        self.assertEqual(BaseStrategyWorker.core_int(settings, "seed"), 42)
        self.assertAlmostEqual(BaseStrategyWorker.core_float(settings, "entry_probability"), 0.06)

    def test_core_float_clamp(self):
        settings = {"core": {"entry_probability": 1.5}}
        self.assertEqual(
            BaseStrategyWorker.core_float(
                settings,
                "entry_probability",
                clamp=(0.0, 1.0),
            ),
            1.0,
        )

    def test_deterministic_roll(self):
        roll = BaseStrategyWorker.deterministic_roll("000001.SZ", "20240102", 42)
        self.assertGreaterEqual(roll, 0.0)
        self.assertLess(roll, 1.0)
        self.assertEqual(
            roll,
            BaseStrategyWorker.deterministic_roll("000001.SZ", "20240102", 42),
        )

    def test_build_opportunity(self):
        worker = _HelperProbeWorker(
            {
                "stock_id": "000001.SZ",
                "execution_mode": "scan",
                "strategy_name": "probe",
                "settings": {
                    "is_enabled": True,
                    "meta": {"display_name": "probe"},
                    "core": {},
                    "data": {"base_required_data": {"data_id": "stock.kline.daily", "params": {"adjust": "qfq"}}},
                },
                "scan_date": "20240102",
            }
        )
        record_of_today = {"date": "20240102", "close": 10.0}
        opp = worker.build_opportunity(record_of_today, extra_fields={"tag": 1})
        self.assertEqual(opp.record_of_today, record_of_today)
        self.assertEqual(opp.stock["id"], "000001.SZ")
        self.assertEqual(opp.extra_fields, {"tag": 1})

    def test_on_calendar_asof_default_selects_all_stocks(self):
        worker = _HelperProbeWorker(
            {
                "stock_id": "000001.SZ",
                "execution_mode": "scan",
                "strategy_name": "probe",
                "settings": {
                    "is_enabled": True,
                    "meta": {"display_name": "probe"},
                    "core": {},
                    "data": {"base_required_data": {"data_id": "stock.kline.daily", "params": {"adjust": "qfq"}}},
                },
                "scan_date": "20240102",
            }
        )
        ctx = CalendarAsOfContext(
            as_of_date="20240102",
            slice_id="slice_0",
            slice_open_days=63,
            window_start="20240102",
            window_end="20240131",
            stocks={"000001.SZ": {"klines": []}, "000002.SZ": {"klines": []}},
            carry={},
            open_date_index=0,
            is_first_open_of_month=True,
            is_last_open_of_month=False,
            is_first_open_of_year=False,
            is_last_open_of_year=False,
        )
        result = worker.on_calendar_asof(ctx, worker.settings.to_dict())
        self.assertEqual(result.selected_stock_ids, ["000001.SZ", "000002.SZ"])


if __name__ == "__main__":
    unittest.main()
