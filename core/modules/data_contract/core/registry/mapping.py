from __future__ import annotations

from typing import Any, Dict, Type, TypedDict

from core.modules.data_contract.core.registry.contract_const import ContractScope, ContractType, DataKey
from core.modules.data_contract.core.load.loaders.base import BaseLoader
from core.modules.data_contract.core.load.loaders.corporate_finance import CorporateFinanceLoader
from core.modules.data_contract.core.load.loaders.index_kline_daily import IndexKlineDailyLoader
from core.modules.data_contract.core.load.loaders.index_list import IndexListLoader
from core.modules.data_contract.core.load.loaders.index_weight_daily import IndexWeightDailyLoader
from core.modules.data_contract.core.load.loaders.macro_cpi import MacroCpiLoader
from core.modules.data_contract.core.load.loaders.macro_gdp import MacroGdpLoader
from core.modules.data_contract.core.load.loaders.macro_lpr import MacroLprLoader
from core.modules.data_contract.core.load.loaders.macro_pmi import MacroPmiLoader
from core.modules.data_contract.core.load.loaders.macro_ppi import MacroPpiLoader
from core.modules.data_contract.core.load.loaders.stock_adj_factor_events import StockAdjFactorEventsLoader
from core.modules.data_contract.core.load.loaders.stock_indicators_daily import StockIndicatorsDailyLoader
from core.modules.data_contract.core.load.loaders.stock_moneyflow_daily import StockMoneyflowDailyLoader
from core.modules.data_contract.core.load.loaders.stock_kline import StockKlineLoader
from core.modules.data_contract.core.load.loaders.stock_list import StockListLoader
from core.modules.data_contract.core.load.loaders.tag import TagLoader
from core.modules.data_contract.core.load.loaders.trade_calendar import TradeCalendarLoader


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


def _stock_kline_spec(*, term: str, display_name: str) -> DataSpec:
    return {
        "scope": ContractScope.PER_ENTITY,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["date", "stock_id"],
        "time_axis_field": "date",
        "time_axis_format": "YYYYMMDD",
        "loader": StockKlineLoader,
        "entity_list_data_id": DataKey.STOCK_LIST,
        "display_name": display_name,
        "defaults": {"term": term},
    }


default_map: DataSpecMap = {
    DataKey.STOCK_LIST: {
        "scope": ContractScope.GLOBAL,
        "type": ContractType.NON_TIME_SERIES,
        "unique_keys": ["id"],
        "loader": StockListLoader,
        "display_name": "股票列表",
        "defaults": {},
    },
    DataKey.STOCK_KLINE_DAILY: _stock_kline_spec(term="daily", display_name="股票日 K 线"),
    DataKey.STOCK_KLINE_WEEKLY: _stock_kline_spec(term="weekly", display_name="股票周 K 线"),
    DataKey.STOCK_KLINE_MONTHLY: _stock_kline_spec(term="monthly", display_name="股票月 K 线"),
    DataKey.TAG: {
        "scope": ContractScope.PER_ENTITY,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["entity_id", "tag_definition_id", "as_of_date"],
        "time_axis_field": "as_of_date",
        "time_axis_format": "YYYYMMDD",
        "loader": TagLoader,
        "entity_list_data_id": DataKey.STOCK_LIST,
        "display_name": "特征标签（按场景）",
        "defaults": {},
    },
    DataKey.STOCK_CORPORATE_FINANCE: {
        "scope": ContractScope.PER_ENTITY,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["id", "quarter"],
        "time_axis_field": "ann_date",
        "time_axis_format": "YYYYMMDD",
        "loader": CorporateFinanceLoader,
        "entity_list_data_id": DataKey.STOCK_LIST,
        "display_name": "公司财报（季频）",
        "defaults": {},
    },
    DataKey.STOCK_INDICATORS_DAILY: {
        "scope": ContractScope.PER_ENTITY,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["id", "date"],
        "time_axis_field": "date",
        "time_axis_format": "YYYYMMDD",
        "loader": StockIndicatorsDailyLoader,
        "entity_list_data_id": DataKey.STOCK_LIST,
        "display_name": "股票日频指标（PE/PB/市值）",
        "defaults": {},
    },
    DataKey.STOCK_MONEYFLOW_DAILY: {
        "scope": ContractScope.PER_ENTITY,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["id", "date"],
        "time_axis_field": "date",
        "time_axis_format": "YYYYMMDD",
        "loader": StockMoneyflowDailyLoader,
        "entity_list_data_id": DataKey.STOCK_LIST,
        "display_name": "个股日频资金流向",
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
        "display_name": "股票复权因子事件",
        "defaults": {},
    },
    DataKey.INDEX_LIST: {
        "scope": ContractScope.GLOBAL,
        "type": ContractType.NON_TIME_SERIES,
        "unique_keys": ["id"],
        "loader": IndexListLoader,
        "display_name": "指数列表",
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
        "display_name": "指数日 K 线",
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
        "display_name": "指数日频成分权重",
        "defaults": {},
    },
    DataKey.MACRO_GDP: {
        "scope": ContractScope.GLOBAL,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["quarter"],
        "time_axis_field": "quarter",
        "time_axis_format": "YYYYQ",
        "loader": MacroGdpLoader,
        "display_name": "宏观 GDP",
        "defaults": {},
    },
    DataKey.MACRO_LPR: {
        "scope": ContractScope.GLOBAL,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["date"],
        "time_axis_field": "date",
        "time_axis_format": "YYYYMMDD",
        "loader": MacroLprLoader,
        "display_name": "宏观 LPR",
        "defaults": {},
    },
    DataKey.MACRO_CPI: {
        "scope": ContractScope.GLOBAL,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["date"],
        "time_axis_field": "date",
        "time_axis_format": "YYYYMM",
        "loader": MacroCpiLoader,
        "display_name": "宏观 CPI",
        "defaults": {},
    },
    DataKey.MACRO_PPI: {
        "scope": ContractScope.GLOBAL,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["date"],
        "time_axis_field": "date",
        "time_axis_format": "YYYYMM",
        "loader": MacroPpiLoader,
        "display_name": "宏观 PPI",
        "defaults": {},
    },
    DataKey.MACRO_PMI: {
        "scope": ContractScope.GLOBAL,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["date"],
        "time_axis_field": "date",
        "time_axis_format": "YYYYMMDD",
        "loader": MacroPmiLoader,
        "display_name": "PMI（采购经理指数）",
        "defaults": {},
    },
    DataKey.TRADE_CALENDAR: {
        "scope": ContractScope.GLOBAL,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["date"],
        "time_axis_field": "date",
        "time_axis_format": "YYYYMMDD",
        "loader": TradeCalendarLoader,
        "display_name": "交易日历",
        "defaults": {},
    },
}
