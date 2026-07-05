from __future__ import annotations

from typing import Dict, Type

from core.modules.data_contract.core.loaders.base import BaseLoader
from core.modules.data_contract.core.loaders.corporate_finance import CorporateFinanceLoader
from core.modules.data_contract.core.loaders.index_kline_daily import IndexKlineDailyLoader
from core.modules.data_contract.core.loaders.index_list import IndexListLoader
from core.modules.data_contract.core.loaders.index_weight_daily import IndexWeightDailyLoader
from core.modules.data_contract.core.loaders.macro_cpi import MacroCpiLoader
from core.modules.data_contract.core.loaders.macro_gdp import MacroGdpLoader
from core.modules.data_contract.core.loaders.macro_lpr import MacroLprLoader
from core.modules.data_contract.core.loaders.macro_pmi import MacroPmiLoader
from core.modules.data_contract.core.loaders.macro_ppi import MacroPpiLoader
from core.modules.data_contract.core.loaders.stock_adj_factor_events import StockAdjFactorEventsLoader
from core.modules.data_contract.core.loaders.stock_indicators_daily import StockIndicatorsDailyLoader
from core.modules.data_contract.core.loaders.stock_moneyflow_daily import StockMoneyflowDailyLoader
from core.modules.data_contract.core.loaders.stock_kline import StockKlineLoader
from core.modules.data_contract.core.loaders.stock_list import StockListLoader
from core.modules.data_contract.core.loaders.tag import TagLoader
from core.modules.data_contract.core.loaders.trade_calendar import TradeCalendarLoader
from core.modules.data_contract.core.system_defaults.data_keys.keys import DataKey


# Loader 映射：DataKey -> Loader 类
LOADER_MAPPING: Dict[DataKey, Type[BaseLoader]] = {
    DataKey.STOCK_LIST: StockListLoader,
    DataKey.STOCK_KLINE_DAILY: StockKlineLoader,
    DataKey.STOCK_KLINE_WEEKLY: StockKlineLoader,
    DataKey.STOCK_KLINE_MONTHLY: StockKlineLoader,
    DataKey.TAG: TagLoader,
    DataKey.STOCK_ADJ_FACTOR_EVENTS: StockAdjFactorEventsLoader,
    DataKey.STOCK_CORPORATE_FINANCE: CorporateFinanceLoader,
    DataKey.STOCK_INDICATORS_DAILY: StockIndicatorsDailyLoader,
    DataKey.STOCK_MONEYFLOW_DAILY: StockMoneyflowDailyLoader,
    DataKey.INDEX_LIST: IndexListLoader,
    DataKey.INDEX_KLINE_DAILY: IndexKlineDailyLoader,
    DataKey.INDEX_WEIGHT_DAILY: IndexWeightDailyLoader,
    DataKey.MACRO_GDP: MacroGdpLoader,
    DataKey.MACRO_LPR: MacroLprLoader,
    DataKey.MACRO_CPI: MacroCpiLoader,
    DataKey.MACRO_PPI: MacroPpiLoader,
    DataKey.MACRO_PMI: MacroPmiLoader,
    DataKey.TRADE_CALENDAR: TradeCalendarLoader,
}


def get_loader(data_key: DataKey) -> Type[BaseLoader]:
    """获取 DataKey 对应的 Loader 类。

    Args:
        data_key: DataKey 枚举

    Returns:
        Loader 类

    Raises:
        KeyError: 如果 DataKey 未注册 loader
    """
    if data_key not in LOADER_MAPPING:
        raise KeyError(f"DataKey {data_key} 未注册 loader")
    return LOADER_MAPPING[data_key]


__all__ = ['LOADER_MAPPING', 'get_loader']