"""时间序列合约基类（扩展时间辅助工具）。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple, Dict, List, Any
from dataclasses import dataclass, field

from .base_contract import BaseDataContract
from core.infra.utils import Utils
@dataclass
class TimeRange:
    """时间范围。"""
    start: str
    end: str


@dataclass
class CursorState:
    """单个 entity 的 cursor 状态。"""
    cursor: int = -1  # 当前索引位置（初始 -1）
    acc: List[Dict[str, Any]] = field(default_factory=list)  # 累积数据（PIT）


class BaseTimeSeriesContract(BaseDataContract):
    """时间序列合约基类（扩展时间辅助工具）。"""

    def __init__(self, declaration: dict):
        """初始化时序合约（扩展父类 __init__）。"""
        # 调用父类 __init__
        super().__init__(declaration)

        # 初始化 cursor 状态
        self._cursor_states: Dict[str, CursorState] = {}
        # until 快路径：全表最早一行时间（normalize 后）；None=未计算，""=无数据
        self._pit_min_date: Optional[str] = None

    def _initialize_cursors(self) -> None:
        """初始化 cursor 状态（在 fill_in_data 后调用）。"""
        if self.data is None:
            return

        if self.is_global():
            # Global scope：单个 cursor
            self._cursor_states = {"_global": CursorState()}
        else:
            # Per entity scope：每个 entity 一个 cursor
            if isinstance(self.data, dict):
                self._cursor_states = {
                    entity_id: CursorState()
                    for entity_id in self.data.keys()
                }
        self._pit_min_date = None

    def _ensure_pit_min_date(self, time_field: str) -> str:
        """缓存全 contract 最早 row 时间，供 until 在 as_of 早于全部数据时整段短路。"""
        if self._pit_min_date is not None:
            return self._pit_min_date
        min_date = ""
        if self.is_global():
            rows = self.data if isinstance(self.data, list) else []
            if rows:
                raw = rows[0].get(time_field)
                if raw is not None:
                    min_date = self.normalize_as_of(str(raw))
        elif isinstance(self.data, dict):
            for rows in self.data.values():
                if not isinstance(rows, list) or not rows:
                    continue
                raw = rows[0].get(time_field)
                if raw is None:
                    continue
                candidate = self.normalize_as_of(str(raw))
                if candidate and (not min_date or candidate < min_date):
                    min_date = candidate
        self._pit_min_date = min_date
        return min_date

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
        """获取时间轴字段名（如 'date', 'quarter', 'ann_date'）。

        Returns:
            str: 时间轴字段名
            None: 如果未定义（返回默认 "date"）

        示例：
            contract = pool.get_contract("stock.kline.daily")
            field = contract.get_base_time_field()
            # field = "date"（从 specific.time_axis_field 或默认值）

        优先级：
        1. runtime.base_time_field（用户指定）
        2. specific.time_axis_field（declaration 定义）
        3. 默认 "date"
        """
        # 从 runtime 读取（用户可能指定）
        if hasattr(self.runtime, 'base_time_field') and self.runtime.base_time_field:
            return self.runtime.base_time_field

        # 从 specific 读取（declaration 定义）
        if hasattr(self.specific, 'time_axis_field') and self.specific.time_axis_field:
            return self.specific.time_axis_field

        # 默认值
        return "date"

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
        return Utils.date.normalize_str(as_of) or as_of

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

    def until(self, as_of: str) -> Dict[str, List[Dict[str, Any]]]:
        """获取 PIT 累计数据（推进 cursor）。

        Args:
            as_of: 时间点（如 '20200101', '2020-01-01', '2020Q1'）

        Returns:
            Dict[entity_id, PIT 数据]:
                - Global scope: {"_global": [累计数据]}
                - Per entity scope: {entity_id: [累计数据]}

        示例：
            contract = issuer.get_contract("stock.kline.daily")
            contract.fill_in_data(runtime={
                "entity_ids": ["600000.SH", "600001.SH"],
                "start_time": "20200101",
                "end_time": "20201231",
            })

            # 推进到 2020-03-01
            pit_data = contract.until(as_of="20200301")
            # pit_data = {
            #     "600000.SH": [截至2020-03-01的累计数据],
            #     "600001.SH": [截至2020-03-01的累计数据],
            # }

        设计：
        - 时间转换只一次（as_of → YYYYMMDD）
        - 累进扫描（从 cursor+1 开始，不重复扫描）
        - 每个 entity 独立 cursor（状态独立）
        - 返回 acc 的引用（不复制数据）
        """
        # 检查是否已加载
        if not self.is_loaded or self.data is None:
            raise ValueError(f"Contract {self.meta.key} 未加载，请先调用 fill_in_data()")

        # 初始化 cursor（如果未初始化）
        if not self._cursor_states:
            self._initialize_cursors()

        # 时间转换（只一次）
        as_of_norm = self.normalize_as_of(as_of)

        # 获取时间字段
        time_field = self.get_base_time_field() or "date"

        # as_of 早于全部数据：无需遍历 entity（空日沉默成本主因）
        pit_min = self._ensure_pit_min_date(time_field)
        if pit_min and as_of_norm < pit_min:
            return {entity_id: state.acc for entity_id, state in self._cursor_states.items()}

        # 遍历所有 entity，推进各自的 cursor
        result = {}
        for entity_id, state in self._cursor_states.items():
            # 获取 entity 数据
            entity_data = self.get_entity_data(entity_id) if entity_id != "_global" else self.data

            if entity_data is None:
                result[entity_id] = []
                continue

            # 从 cursor+1 开始扫描（累进扫描）
            before_cursor = state.cursor
            i = before_cursor + 1
            n = len(entity_data)
            new_cursor = before_cursor

            while i < n:
                row = entity_data[i]
                row_time = row.get(time_field)

                if row_time is None:
                    i += 1
                    continue

                # 规范化 row 时间
                row_time_norm = self.normalize_as_of(str(row_time))

                # 如果 row_time > as_of，停止
                if row_time_norm > as_of_norm:
                    break

                # 加入 acc（引用，不复制）
                state.acc.append(row)
                new_cursor = i
                i += 1

            # 更新 cursor
            state.cursor = new_cursor

            # 返回 acc（引用）
            result[entity_id] = state.acc

        return result

    def reset_cursor(self) -> None:
        """重置 cursor 状态。

        清空所有 entity 的 cursor 状态（cursor=-1, acc=[]）。

        示例：
            contract.until(as_of="20200301")  # cursor 推进到3月
            contract.reset_cursor()  # 重置
            contract.until(as_of="20200101")  # 从头开始扫描
        """
        for state in self._cursor_states.values():
            state.cursor = -1
            state.acc = []

    def fill_in_data(self, runtime: Optional[dict] = None, force_reload: bool = False) -> 'BaseTimeSeriesContract':
        """填充数据（扩展父类方法，添加 cursor 初始化）。

        Args:
            runtime: 运行时信息（可选）
            force_reload: 是否强制重新加载

        Returns:
            self（支持链式调用）

        设计：
        - 调用父类的 fill_in_data（加载数据）
        - 初始化 cursor 状态（准备 until 调用）
        """
        # 调用父类的 fill_in_data
        super().fill_in_data(runtime=runtime, force_reload=force_reload)

        # 初始化 cursor
        self._initialize_cursors()

        return self

