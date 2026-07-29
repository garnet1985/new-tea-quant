"""non_time_series Tag：轻量主进程一次计算（不走 BacktestEngine）。

实体池复用 global 哨兵 ``GLOBAL_ENTITY_ID``；钩子复用 ``calculate_tag``。
"""

from core.modules.tag.core.engines.global_based.constants import GLOBAL_ENTITY_ID
from core.modules.tag.core.engines.non_time_series.data_loader import (
    TagNonTimeSeriesDataLoader,
)
from core.modules.tag.core.engines.non_time_series.pipeline import (
    TagNonTimeSeriesPipeline,
)

__all__ = [
    "GLOBAL_ENTITY_ID",
    "TagNonTimeSeriesDataLoader",
    "TagNonTimeSeriesPipeline",
]
