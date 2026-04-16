from __future__ import annotations

from typing import Any, Dict, Type, TypedDict

from core.modules.data_contract.contract_const import ContractScope, ContractType, DataKey
from core.modules.data_contract.loaders.base import BaseLoader
from core.modules.data_contract.loaders.corporate_finance import CorporateFinanceLoader
from core.modules.data_contract.loaders.index_kline_daily import IndexKlineDailyLoader
from core.modules.data_contract.loaders.index_list import IndexListLoader
from core.modules.data_contract.loaders.index_weight_daily import IndexWeightDailyLoader
from core.modules.data_contract.loaders.macro_cpi import MacroCpiLoader
from core.modules.data_contract.loaders.macro_gdp import MacroGdpLoader
from core.modules.data_contract.loaders.macro_lpr import MacroLprLoader
from core.modules.data_contract.loaders.macro_pmi import MacroPmiLoader
from core.modules.data_contract.loaders.macro_ppi import MacroPpiLoader
from core.modules.data_contract.loaders.stock_adj_factor_events import StockAdjFactorEventsLoader
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
    entity_list_data_id: DataKey
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
    DataKey.STOCK_KLINE: {
        "scope": ContractScope.PER_ENTITY,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["date", "stock_id"],
        "time_axis_field": "date",
        "time_axis_format": "YYYYMMDD",
        "loader": StockKlineLoader,
        "entity_list_data_id": DataKey.STOCK_LIST,
        "display_name": "Stock Kline（由 params 指定 adjust/term）",
        "defaults": {},
    },
    # 统一 tag：存储含 as_of_date，故为时序；通过 tag_scenario / scenario_id 区分场景（见 TagLoader）
    DataKey.TAG: {
        "scope": ContractScope.PER_ENTITY,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["entity_id", "tag_definition_id", "as_of_date"],
        "time_axis_field": "as_of_date",
        "time_axis_format": "YYYYMMDD",
        "loader": TagLoader,
        "entity_list_data_id": DataKey.STOCK_LIST,
        "display_name": "Tag（按 scenario）",
        "defaults": {},
    },
    DataKey.STOCK_CORPORATE_FINANCE: {
        "scope": ContractScope.PER_ENTITY,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["id", "quarter"],
        "time_axis_field": "quarter",
        "time_axis_format": "YYYYQ",
        "loader": CorporateFinanceLoader,
        "entity_list_data_id": DataKey.STOCK_LIST,
        "display_name": "Corporate Finance (quarterly)",
        "defaults": {},
    },
    DataKey.STOCK_ADJ_FACTOR_EVENTS: {
        "scope": ContractScope.PER_ENTITY,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["id", "event_date"],
        "time_axis_field": "event_date",
        "time_axis_format": "YYYYMMDD",
        "loader": StockAdjFactorEventsLoader,
        "entity_list_data_id": DataKey.STOCK_LIST,
        "display_name": "Stock Adj Factor Events",
        "defaults": {},
    },
    DataKey.INDEX_LIST: {
        "scope": ContractScope.GLOBAL,
        "type": ContractType.NON_TIME_SERIES,
        "unique_keys": ["id"],
        "loader": IndexListLoader,
        "display_name": "Index List",
        "defaults": {},
    },
    DataKey.INDEX_KLINE_DAILY: {
        "scope": ContractScope.PER_ENTITY,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["id", "term", "date"],
        "time_axis_field": "date",
        "time_axis_format": "YYYYMMDD",
        "loader": IndexKlineDailyLoader,
        "entity_list_data_id": DataKey.INDEX_LIST,
        "display_name": "Index Kline Daily",
        "defaults": {},
    },
    DataKey.INDEX_WEIGHT_DAILY: {
        "scope": ContractScope.PER_ENTITY,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["id", "date", "stock_id"],
        "time_axis_field": "date",
        "time_axis_format": "YYYYMMDD",
        "loader": IndexWeightDailyLoader,
        "entity_list_data_id": DataKey.INDEX_LIST,
        "display_name": "Index Weight Daily",
        "defaults": {},
    },
    DataKey.MACRO_GDP: {
        "scope": ContractScope.GLOBAL,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["quarter"],
        "time_axis_field": "quarter",
        "time_axis_format": "YYYYQ",
        "loader": MacroGdpLoader,
        "display_name": "Macro GDP",
        "defaults": {},
    },
    DataKey.MACRO_LPR: {
        "scope": ContractScope.GLOBAL,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["date"],
        "time_axis_field": "date",
        "time_axis_format": "YYYYMMDD",
        "loader": MacroLprLoader,
        "display_name": "Macro LPR",
        "defaults": {},
    },
    DataKey.MACRO_CPI: {
        "scope": ContractScope.GLOBAL,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["date"],
        "time_axis_field": "date",
        "time_axis_format": "YYYYMM",
        "loader": MacroCpiLoader,
        "display_name": "Macro CPI",
        "defaults": {},
    },
    DataKey.MACRO_PPI: {
        "scope": ContractScope.GLOBAL,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["date"],
        "time_axis_field": "date",
        "time_axis_format": "YYYYMM",
        "loader": MacroPpiLoader,
        "display_name": "Macro PPI",
        "defaults": {},
    },
    DataKey.MACRO_PMI: {
        "scope": ContractScope.GLOBAL,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["date"],
        "time_axis_field": "date",
        "time_axis_format": "YYYYMM",
        "loader": MacroPmiLoader,
        "display_name": "Macro PMI",
        "defaults": {},
    },
}
