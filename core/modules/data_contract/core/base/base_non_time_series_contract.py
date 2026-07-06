"""非时间序列合约基类（无时间辅助工具）。"""
from __future__ import annotations

from .base_contract import BaseDataContract


class BaseNonTimeSeriesContract(BaseDataContract):
    """非时间序列合约基类（无时间辅助工具）。

    特点：
    - 没有 start_time/end_time
    - 没有 base_time_field/time_format
    - 没有时间辅助工具的API（get_time_window, normalize_as_of 等）
    """
    pass