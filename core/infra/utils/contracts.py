"""跨模块契约：周期类型与归档格式常量。

推荐::

    from core.infra.utils import Utils
    from core.infra.utils.contracts import PERIOD_DAY, ArchiveFormat
"""

from __future__ import annotations

from typing import Literal

from core.infra.utils.date.constants import (
    PERIOD_DAY,
    PERIOD_MONTH,
    PERIOD_QUARTER,
    PERIOD_WEEK,
    PERIOD_YEAR,
)

ArchiveFormat = Literal["tar.gz", "zip"]
PeriodType = Literal["day", "week", "month", "quarter", "year"]

__all__ = [
    "PERIOD_DAY",
    "PERIOD_WEEK",
    "PERIOD_MONTH",
    "PERIOD_QUARTER",
    "PERIOD_YEAR",
    "ArchiveFormat",
    "PeriodType",
]
