"""stock.st_periods contract + StrategyDataResolver 自动注入。"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.force_run

from core.modules.data_contract import DATA_KEY, ContractIssuer
from core.modules.data_contract.core.data_contracts.stock_st_periods.contract import (
    StockStPeriodsContract,
)
from core.modules.strategy.core.services.entity_loader.strategy_data_resolver import (
    StrategyDataResolver,
)


def _periods() -> List[Dict[str, Any]]:
    return [
        {
            "stock_id": "600000.SH",
            "st_level": "ST",
            "start_date": "20240101",
            "end_date": "20240131",
        },
        {
            "stock_id": "600000.SH",
            "st_level": "STAR_ST",
            "start_date": "20240201",
            "end_date": "20240228",
        },
    ]


def _contract_with_data(rows_by_entity: Dict[str, List[Dict[str, Any]]]) -> StockStPeriodsContract:
    declaration = {
        "meta": {
            "key": DATA_KEY.STOCK_ST_PERIODS,
            "type": "time_series",
            "scope": "per_entity",
            "display_name": "test",
            "loader": MagicMock,
        },
        "specific": {},
    }
    contract = StockStPeriodsContract(declaration)
    contract.data = rows_by_entity
    contract.is_loaded = True
    contract.runtime.entity_ids = list(rows_by_entity.keys())
    return contract


class TestStockStPeriodsContractAPI:
    def test_status_tags_and_level_at(self) -> None:
        contract = _contract_with_data({"600000.SH": _periods()})
        assert contract.status_tags_at("600000.SH", "20240115") == ["st"]
        assert contract.level_at("600000.SH", "20240115") == "st"
        assert contract.status_tags_at("600000.SH", "20240210") == ["star_st"]
        assert contract.level_at("600000.SH", "20240210") == "star_st"
        assert contract.status_tags_at("600000.SH", "20240301") == []
        assert contract.level_at("600000.SH", "20240301") is None

    def test_unknown_entity_empty(self) -> None:
        contract = _contract_with_data({"600000.SH": _periods()})
        assert contract.periods_for("999999.SH") == []
        assert contract.status_tags_at("999999.SH", "20240115") == []


class TestStrategyDataResolverAutoInject:
    def test_auto_injects_st_periods_for_stock_kline_base(self) -> None:
        resolver = StrategyDataResolver(
            {
                "data": {
                    "base": {"data_key": "stock.kline.daily", "params": {}},
                    "required": [],
                }
            }
        )
        keys = [item["data_key"] for item in resolver.issue_declarations()]
        assert DATA_KEY.STOCK_ST_PERIODS in keys
        assert keys[0] == "stock.kline.daily"

    def test_does_not_duplicate_when_user_declared(self) -> None:
        resolver = StrategyDataResolver(
            {
                "data": {
                    "base": {"data_key": "stock.kline.daily", "params": {}},
                    "required": [
                        {"data_key": DATA_KEY.STOCK_ST_PERIODS, "params": {}},
                    ],
                }
            }
        )
        keys = [item["data_key"] for item in resolver.issue_declarations()]
        assert keys.count(DATA_KEY.STOCK_ST_PERIODS) == 1

    def test_skips_when_base_not_stock_kline(self) -> None:
        resolver = StrategyDataResolver(
            {
                "data": {
                    "base": {"data_key": "index.kline.daily", "params": {}},
                    "required": [],
                }
            }
        )
        keys = [item["data_key"] for item in resolver.issue_declarations()]
        assert DATA_KEY.STOCK_ST_PERIODS not in keys


class TestStockStPeriodsDiscovery:
    def test_issuer_discovers_stock_st_periods(self) -> None:
        ContractIssuer._discovered = False
        ContractIssuer._declarations_cache = {}
        contract = ContractIssuer.issue(DATA_KEY.STOCK_ST_PERIODS, fill_in_data=False)
        assert isinstance(contract, StockStPeriodsContract)
        assert contract.meta.key == DATA_KEY.STOCK_ST_PERIODS
        assert contract.is_time_series()
        assert contract.get_base_time_field() == "start_date"
