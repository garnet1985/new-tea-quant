from __future__ import annotations

from typing import Any, Dict, Type, TypedDict

from core.modules.data_contract.contract_const import ContractScope, ContractType, DataKey
from core.modules.data_contract.loaders.base import BaseLoader
from core.modules.data_contract.loaders.stock_kline import StockKlineLoader
from core.modules.data_contract.loaders.stock_list import StockListLoader
from core.modules.data_contract.loaders.tag import TagLoader


class DataSpec(TypedDict, total=False):
    scope: ContractScope
    type: ContractType
    unique_keys: list[str]
    time_axis_field: str
    time_axis_format: str
    loader: Type[BaseLoader]
    display_name: str
    defaults: Dict[str, Any]


DataSpecMap = Dict[DataKey, DataSpec]


default_map: DataSpecMap = {
    DataKey.STOCK_LIST: {
        "scope": ContractScope.GLOBAL,
        "type": ContractType.NON_TIME_SERIES,
        "unique_keys": ["id"],
        "loader": StockListLoader,
        "display_name": "Stock List",
        "defaults": {},
    },
    DataKey.STOCK_KLINE_DAILY_QFQ: {
        "scope": ContractScope.PER_ENTITY,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["date", "stock_id"],
        "time_axis_field": "date",
        "time_axis_format": "YYYYMMDD",
        "loader": StockKlineLoader,
        "display_name": "Stock Kline Daily QFQ",
        "defaults": {"adjust": "qfq", "term": "daily"},
    },
    DataKey.STOCK_KLINE_DAILY_NFQ: {
        "scope": ContractScope.PER_ENTITY,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["date", "stock_id"],
        "time_axis_field": "date",
        "time_axis_format": "YYYYMMDD",
        "loader": StockKlineLoader,
        "display_name": "Stock Kline Daily NFQ",
        "defaults": {"adjust": "nfq", "term": "daily"},
    },
    # 统一 tag：存储含 as_of_date，故为时序；通过 tag_scenario / scenario_id 区分场景（见 TagLoader）
    DataKey.TAG: {
        "scope": ContractScope.PER_ENTITY,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["entity_id", "tag_definition_id", "as_of_date"],
        "time_axis_field": "as_of_date",
        "time_axis_format": "YYYYMMDD",
        "loader": TagLoader,
        "display_name": "Tag（按 scenario）",
        "defaults": {},
    },
}
