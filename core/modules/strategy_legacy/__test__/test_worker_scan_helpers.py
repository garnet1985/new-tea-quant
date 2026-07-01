#!/usr/bin/env python3
"""StrategyHooks scan 辅助方法单元测试。"""

from __future__ import annotations

import unittest
from typing import Optional

from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.types import (
    CalendarAsOfContext,
)
from core.modules.strategy.hooks import (
    StrategyHooks,
    calendar_asof_context,
    scan_context,
)


class _HelperProbeHooks(StrategyHooks):
    def scan_opportunity(self, ctx) -> Optional[Opportunity]:
        return None


def _minimal_settings() -> StrategySettingsView:
    return StrategySettingsView.from_dict(
        {
            "is_enabled": True,
            "meta": {"display_name": "probe"},
            "core": {},
            "data": {
                "base_required_data": {
                    "data_id": "stock.kline.daily",
                    "params": {"adjust": "qfq"},
                }
            },
        }
    )


class TestStrategyHooksHelpers(unittest.TestCase):
    def test_get_record_of_today_empty(self):
        self.assertIsNone(StrategyHooks.get_record_of_today({}))
        self.assertIsNone(StrategyHooks.get_record_of_today({"klines": []}))

    def test_get_record_of_today_latest(self):
        data = {"klines": [{"date": "20240101"}, {"date": "20240102"}]}
        self.assertEqual(StrategyHooks.get_record_of_today(data), {"date": "20240102"})

    def test_signal_date(self):
        record_of_today = {"date": "20240614"}
        self.assertEqual(StrategyHooks.signal_date(record_of_today), "20240614")

    def test_core_int_and_float(self):
        settings = {"core": {"seed": "42", "entry_probability": "0.06"}}
        self.assertEqual(StrategyHooks.core_int(settings, "seed"), 42)
        self.assertAlmostEqual(StrategyHooks.core_float(settings, "entry_probability"), 0.06)

    def test_core_float_clamp(self):
        settings = {"core": {"entry_probability": 1.5}}
        self.assertEqual(
            StrategyHooks.core_float(
                settings,
                "entry_probability",
                clamp=(0.0, 1.0),
            ),
            1.0,
        )

    def test_deterministic_roll(self):
        roll = StrategyHooks.deterministic_roll("000001.SZ", "20240102", 42)
        self.assertGreaterEqual(roll, 0.0)
        self.assertLess(roll, 1.0)
        self.assertEqual(
            roll,
            StrategyHooks.deterministic_roll("000001.SZ", "20240102", 42),
        )

    def test_build_opportunity(self):
        hooks = _HelperProbeHooks()
        settings = _minimal_settings()
        ctx = scan_context(
            strategy_name="probe",
            settings=settings,
            stock_id="000001.SZ",
            job_payload={"stock_id": "000001.SZ"},
            stock_info={"id": "000001.SZ", "name": "000001.SZ"},
            data={},
            scan_date="20240102",
        )
        record_of_today = {"date": "20240102", "close": 10.0}
        opp = hooks.build_opportunity(ctx, record_of_today, extra_fields={"tag": 1})
        self.assertEqual(opp.record_of_today, record_of_today)
        self.assertEqual(opp.stock["id"], "000001.SZ")
        self.assertEqual(opp.extra_fields, {"tag": 1})

    def test_on_calendar_asof_default_selects_all_stocks(self):
        hooks = _HelperProbeHooks()
        settings = _minimal_settings()
        calendar = CalendarAsOfContext(
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
        ctx = calendar_asof_context(
            strategy_name="probe",
            settings=settings,
            calendar=calendar,
        )
        result = hooks.on_calendar_asof(ctx)
        self.assertEqual(result.selected_stock_ids, ["000001.SZ", "000002.SZ"])


if __name__ == "__main__":
    unittest.main()
