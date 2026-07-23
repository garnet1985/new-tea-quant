"""StockStPeriods Declaration。"""

from __future__ import annotations

from typing import Any, Dict

from ..data_keys import SYS_DATA_KEY
from .contract import StockStPeriodsContract
from .loader import StockStPeriodsLoader


STOCK_ST_PERIODS_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": SYS_DATA_KEY.STOCK_ST_PERIODS,
        "type": "time_series",
        "scope": "per_entity",
        "display_name": "股票 ST / *ST 警示时段",
        "description": "sys_stock_st_periods；区间时序；供涨跌停 status_tags 与风控查询",
        "unique_keys": ["stock_id", "st_level", "start_date"],
        "loader": StockStPeriodsLoader,
        "contract_class": StockStPeriodsContract,
    },
    "specific": {},
}


__all__ = ["STOCK_ST_PERIODS_DECLARATION"]
