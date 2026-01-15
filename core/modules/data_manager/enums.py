from enum import Enum

class BaseTableNames(Enum):
    stock_kline = 'stock_kline'
    # adj_factor 已废弃，使用 adj_factor_event 替代
    # adj_factor = 'adj_factor'
    adj_factor_events = 'adj_factor_events'
    stock_list = 'stock_list'