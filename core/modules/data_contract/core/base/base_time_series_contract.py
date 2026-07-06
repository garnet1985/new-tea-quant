"""时间序列合约基类（扩展时间辅助工具）。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple
from dataclasses import dataclass

from .base_contract import BaseDataContract
from core.utils.date.date_utils import DateUtils


@dataclass
class TimeRange:
    """时间范围。"""
    start: str
    end: str


class BaseTimeSeriesContract(BaseDataContract):
    """时间序列合约基类（扩展时间辅助工具）。"""

    def get_time_window(self) -> Optional[TimeRange]:
        """获取时间窗口（用户定义的时间范围）。

        Returns:
            TimeRange: 时间范围（start_time, end_time）
            None: 如果未定义时间范围

        示例：
            contract = pool.get_contract("stock.kline.daily")
            contract.fill_in_data(runtime={
                "start_time": "20200101",
                "end_time": "20201231",
            })
            window = contract.get_time_window()
            # window.start = "20200101", window.end = "20201231"
        """
        if not self.runtime.start_time or not self.runtime.end_time:
            return None

        return TimeRange(
            start=self.runtime.start_time,
            end=self.runtime.end_time,
        )

    def get_base_time_field(self) -> Optional[str]:
        """获取时间轴字段名（如 'date', 'quarter'）。

        Returns:
            str: 时间轴字段名
            None: 如果未定义

        示例：
            contract = pool.get_contract("stock.kline.daily")
            field = contract.get_base_time_field()
            # field = "date"（从 runtime.base_time_field 或 spec 读取）
        """
        # 从 runtime 读取（用户可能指定）
        if self.runtime.base_time_field:
            return self.runtime.base_time_field

        # 从 spec 读取（默认值）
        # TODO: 从 specific 或 meta 中读取默认的 base_time_field
        return None

    def get_time_format(self) -> Optional[str]:
        """获取时间格式（如 'YYYYMMDD', 'YYYY-MM-DD', 'YYYYQ'）。

        Returns:
            str: 时间格式
            None: 如果未定义

        示例：
            contract = pool.get_contract("stock.kline.daily")
            format = contract.get_time_format()
            # format = "YYYYMMDD"
        """
        # 从 runtime 读取（用户可能指定）
        if self.runtime.time_format:
            return self.runtime.time_format

        # 从 spec 读取（默认值）
        # TODO: 从 specific 或 meta 中读取默认的 time_format
        return None

    def normalize_as_of(self, as_of: str) -> str:
        """标准化时间格式（统一为 YYYYMMDD，内部通用格式）。

        Args:
            as_of: 输入时间字符串（如 '2020-01-01', '20200101', '2020Q1'）

        Returns:
            str: 标准化后的时间字符串（YYYYMMDD 格式）

        示例：
            contract = pool.get_contract("stock.kline.daily")
            normalized = contract.normalize_as_of("2020-01-01")
            # normalized = "20200101"

            normalized = contract.normalize_as_of("2020Q1")
            # normalized = "20200101"（季度转换为该季度第一天）
        """
        return DateUtils.normalize_str(as_of) or as_of

    def is_in_time_window(self, start_time: str, end_time: str) -> bool:
        """检查时间范围是否在当前时间窗口内。

        Args:
            start_time: 开始时间点（如 '20200101'）
            end_time: 结束时间点（如 '20201231'）

        Returns:
            bool: 是否在时间窗口内
        """
        window = self.get_time_window()
        if window is None:
            return False

        return window.contains(start_time) and window.contains(end_time)

    # TODO: these APIs currently does not have any cases and complicated, so won't implement for now
    # def extend_data(self, new_end_time: str) -> None:
    #     """扩展数据到新时间点（动态加载新数据）。

    #     Args:
    #         new_end_time: 新的结束时间点

    #     示例：
    #         contract = pool.get_contract("stock.kline.daily")
    #         contract.fill_in_data(runtime={
    #             "start_time": "20200101",
    #             "end_time": "20201231",
    #         })
    #         contract.extend_data("20210101")  # 扩展到2021年
    #     """
    #     raise NotImplementedError("extend_data 尚未实现")

    # def shrink_data(self, new_end_time: str) -> None:
    #     """收缩数据到新时间点（释放内存）。

    #     Args:
    #         new_end_time: 新的结束时间点

    #     示例：
    #         contract = pool.get_contract("stock.kline.daily")
    #         contract.fill_in_data(runtime={
    #             "start_time": "20200101",
    #             "end_time": "20201231",
    #         })
    #         contract.shrink_data("20201001")  # 收缩到2020年10月
    #     """
    #     raise NotImplementedError("shrink_data 尚未实现")


