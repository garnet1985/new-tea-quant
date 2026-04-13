"""
Contracts package.

MVP: framework-internal rule classes (not user-extensible).

四类规则类命名与 `CONCEPTS.md` §5 对齐：**全局/单实体 × 时序/非时序**。
"""

from .base import BaseContract, ContractScope, GlobalContract, PerEntityContract
from .entity_non_timeseries import EntityNonTimeseriesContract, RawEntityNonTimeseries
from .entity_timeseries import EntityTimeseriesContract
from .global_non_timeseries import GlobalNonTimeseriesContract, RawGlobalNonTimeseries
from .global_timeseries import GlobalTimeseriesContract

__all__ = [
    "BaseContract",
    "ContractScope",
    "EntityNonTimeseriesContract",
    "EntityTimeseriesContract",
    "GlobalContract",
    "GlobalNonTimeseriesContract",
    "GlobalTimeseriesContract",
    "PerEntityContract",
    "RawEntityNonTimeseries",
    "RawGlobalNonTimeseries",
]
