"""基础表名常量（与 core/tables schema.name 对齐；运行时以 discovery 为准）。"""

from enum import Enum


class BaseTableNames(Enum):
    STOCK_KLINES = "sys_stock_klines"
    ADJ_FACTOR_EVENTS = "sys_adj_factor_events"
    STOCK_LIST = "sys_stock_list"
