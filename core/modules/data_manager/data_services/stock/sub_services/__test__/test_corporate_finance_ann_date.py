#!/usr/bin/env python3
"""Corporate finance PIT 时间轴（ann_date）单元测试。"""

from __future__ import annotations

import unittest

from core.modules.data_contract.contract_const import ContractScope, ContractType, DataKey
from core.modules.data_contract.contracts.base import DataContract
from core.modules.data_contract.data_class.contract_meta import ContractMeta
from core.modules.data_cursor.data_cursor import DataCursor
from core.modules.data_manager.data_services.stock.sub_services.corporate_finance_service import (
    CorporateFinanceService,
)


def _finance_meta() -> ContractMeta:
    return ContractMeta(
        data_id=DataKey.STOCK_CORPORATE_FINANCE,
        name=DataKey.STOCK_CORPORATE_FINANCE.value,
        scope=ContractScope.PER_ENTITY,
        attrs={
            "type": ContractType.TIME_SERIES,
            "time_axis_field": "ann_date",
            "time_axis_format": "YYYYMMDD",
        },
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

    def test_data_cursor_until_uses_ann_date_pit(self):
        rows = [
            {"quarter": "2024Q1", "ann_date": "20240430", "netprofit_yoy": 1.0},
            {"quarter": "2024Q2", "ann_date": "20240831", "netprofit_yoy": 2.0},
            {"quarter": "2024Q3", "ann_date": "20241030", "netprofit_yoy": 3.0},
        ]
        contract = DataContract(meta=_finance_meta(), data=rows)

        cursor_before_q2 = DataCursor(contracts={"stock.finance.quarterly": contract})
        prefix_before_q2 = cursor_before_q2.until("20240830")["stock.finance.quarterly"]
        self.assertEqual([row["quarter"] for row in prefix_before_q2], ["2024Q1"])

        cursor_mid = DataCursor(
            contracts={
                "stock.finance.quarterly": DataContract(meta=_finance_meta(), data=list(rows))
            }
        )
        prefix_mid = cursor_mid.until("20240915")["stock.finance.quarterly"]
        self.assertEqual([row["quarter"] for row in prefix_mid], ["2024Q1", "2024Q2"])

        cursor_all = DataCursor(
            contracts={
                "stock.finance.quarterly": DataContract(meta=_finance_meta(), data=list(rows))
            }
        )
        prefix_all = cursor_all.until("20241101")["stock.finance.quarterly"]
        self.assertEqual(
            [row["quarter"] for row in prefix_all],
            ["2024Q1", "2024Q2", "2024Q3"],
        )


if __name__ == "__main__":
    unittest.main()
