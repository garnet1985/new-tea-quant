"""
时序实体：带时间维度的 Entity（如 K 线、宏观指标）

在 Entity 数据契约基础上增加时间字段约定，便于 data source 的 renew 与写入。
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.data_class.entity.entity import Entity


@dataclass
class TimeSerialEntity(Entity):
    """时序实体：含日期/周期约定"""

    date_field: str = "date"
    """日期字段名，如 'date', 'trade_date'"""

    term: Optional[str] = None
    """周期（若单表多周期用 term 列区分），如 'daily', 'weekly', 'monthly'；按 term 分表时可为 None"""
