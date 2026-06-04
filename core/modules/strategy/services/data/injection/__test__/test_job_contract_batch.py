"""StrategyJobContractBatch 单元测试。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_ROOT = Path(__file__).resolve().parents[6]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    import pandas as _pandas  # noqa: F401
except ImportError:
    import types

    _pd = types.ModuleType("pandas")
    _pd.DataFrame = object  # type: ignore[attr-defined]
    sys.modules["pandas"] = _pd

from core.modules.data_contract.cache import ContractCacheManager
from core.modules.data_contract.contract_const import ContractScope, DataKey
from core.modules.data_contract.contracts import DataContract
from core.modules.data_contract.data_class.contract_meta import ContractMeta
from core.modules.data_contract.data_class.issue_result import IssueResult
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.services.data.injection.job_contract_batch import (
    StrategyJobContractBatch,
)


def _meta(dk: DataKey, scope: ContractScope) -> ContractMeta:
    return ContractMeta(data_id=dk, name=dk.value, scope=scope)


def _contract(dk: DataKey, scope: ContractScope, data=None) -> DataContract:
    return DataContract(meta=_meta(dk, scope), data=data)


class TestStrategyJobContractBatch(unittest.TestCase):
    def test_contracts_for_entity_merges_global_and_per_entity(self) -> None:
        global_c = _contract(DataKey.STOCK_LIST, ContractScope.GLOBAL, [{"id": "600000.SH"}])
        kline_a = _contract(DataKey.STOCK_KLINE, ContractScope.PER_ENTITY, [{"date": "20200101"}])
        kline_b = _contract(DataKey.STOCK_KLINE, ContractScope.PER_ENTITY, [{"date": "20200201"}])
        batch = StrategyJobContractBatch(
            global_contracts={DataKey.STOCK_LIST: global_c},
            per_entity_results={
                DataKey.STOCK_KLINE: IssueResult(
                    data_id=DataKey.STOCK_KLINE,
                    scope=ContractScope.PER_ENTITY,
                    by_entity={
                        "600000.SH": kline_a,
                        "600001.SH": kline_b,
                    },
                )
            },
        )
        merged = batch.contracts_for_entity("600000.SH")
        self.assertIs(merged[DataKey.STOCK_LIST], global_c)
        self.assertIs(merged[DataKey.STOCK_KLINE], kline_a)
        self.assertEqual(merged[DataKey.STOCK_KLINE].data[0]["date"], "20200101")

    @patch("core.modules.strategy.services.data.injection.job_contract_batch.DataContractManager")
    def test_hydrate_issues_batch_for_per_entity(self, mock_dcm_cls: MagicMock) -> None:
        mock_dcm = MagicMock()
        mock_dcm_cls.return_value = mock_dcm
        mock_dcm.map.get.side_effect = lambda dk: {
            "scope": (
                ContractScope.PER_ENTITY
                if dk == DataKey.STOCK_KLINE
                else ContractScope.GLOBAL
            ),
            "type": "time_series",
        }

        kline_result = IssueResult(
            data_id=DataKey.STOCK_KLINE,
            scope=ContractScope.PER_ENTITY,
            by_entity={"600000.SH": _contract(DataKey.STOCK_KLINE, ContractScope.PER_ENTITY, [])},
        )
        global_contract = _contract(DataKey.STOCK_LIST, ContractScope.GLOBAL, [])
        mock_dcm.issue.side_effect = [kline_result, MagicMock(require_contract=lambda: global_contract)]

        settings = StrategySettingsView.from_dict(
            {
                "data": {
                    "base_required_data": {
                        "params": {"term": "daily", "adjust": "qfq"},
                    },
                    "extra_required_data_sources": [
                        {"data_id": DataKey.STOCK_LIST.value, "params": {}},
                    ],
                }
            }
        )

        batch = StrategyJobContractBatch.hydrate(
            entity_ids=["600000.SH"],
            settings=settings,
            start="20200101",
            end="20201231",
            contract_cache=ContractCacheManager(),
        )

        self.assertIn(DataKey.STOCK_KLINE, batch.per_entity_results)
        per_entity_call = mock_dcm.issue.call_args_list[0]
        self.assertEqual(per_entity_call.kwargs.get("entity_ids"), ["600000.SH"])
        self.assertEqual(batch.contracts_for_entity("600000.SH")[DataKey.STOCK_KLINE].data, [])


if __name__ == "__main__":
    unittest.main()
