#!/usr/bin/env python3
"""Corporate finance PIT 时间轴（ann_date）单元测试。"""

from __future__ import annotations

import unittest

from core.modules.data_manager.core.data_services.stock.sub_services.corporate_finance_service import (
    CorporateFinanceService,
)


class TestCorporateFinanceAnnDate(unittest.TestCase):
    def test_prepare_time_series_rows_sorts_and_filters(self):
        rows = CorporateFinanceService._prepare_time_series_rows(
            [
                {"quarter": "2024Q3", "ann_date": "20241030", "netprofit_yoy": 3.0},
                {"quarter": "2024Q1", "ann_date": "20240430", "netprofit_yoy": 1.0},
                {"quarter": "2024Q2", "ann_date": None, "netprofit_yoy": 2.0},
            ]
        )
        self.assertEqual([row["quarter"] for row in rows], ["2024Q1", "2024Q3"])

    def test_ann_date_pit_prefix_semantics(self):
        """Loader 按 ann_date 排序后，PIT 前缀由 data_contract.until（time_axis=ann_date）推进。"""
        rows = CorporateFinanceService._prepare_time_series_rows(
            [
                {"quarter": "2024Q1", "ann_date": "20240430", "netprofit_yoy": 1.0},
                {"quarter": "2024Q2", "ann_date": "20240831", "netprofit_yoy": 2.0},
                {"quarter": "2024Q3", "ann_date": "20241030", "netprofit_yoy": 3.0},
            ]
        )

        def _prefix(as_of: str):
            return [r for r in rows if str(r["ann_date"]) <= as_of]

        self.assertEqual([r["quarter"] for r in _prefix("20240830")], ["2024Q1"])
        self.assertEqual(
            [r["quarter"] for r in _prefix("20240915")], ["2024Q1", "2024Q2"]
        )
        self.assertEqual(
            [r["quarter"] for r in _prefix("20241101")],
            ["2024Q1", "2024Q2", "2024Q3"],
        )


if __name__ == "__main__":
    unittest.main()
