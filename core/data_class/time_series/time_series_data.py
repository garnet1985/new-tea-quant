#!/usr/bin/env python3
"""
TimeSeriesData：时序数据块封装

设计目标：
- 使用 ColumnarTable 承载一段具体的时序数据（如某只股票的一段 K 线）
- 提供按日期推进游标、迭代「截至某日的所有数据」等基础能力
- 可选关联 Entity 用于描述表/字段契约，但不强绑定 DB 模型
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Iterator, Iterable

from core.data_class.time_series.columnar import ColumnarTable, RowView
from core.data_class.entity import Entity


@dataclass
class TimeSeriesData:
    """
    时序数据块（列式 + 游标）。

    - name: 可选的人类可读名称（如 'StockKlineDaily'）
    - entity: 可选的 Entity 契约引用（表/字段元信息）
    - date_field: 日期字段名（默认为 'date'）
    - term: 周期信息（如 'daily' / 'weekly'）
    - table: 列式数据表（ColumnarTable）
    - cursor: 游标位置（初始为 -1，表示尚未推进）
    """

    name: str
    date_field: str = "date"
    term: Optional[str] = None
    entity: Optional[Entity] = None

    table: Optional[ColumnarTable] = field(default=None, repr=False)
    cursor: int = -1

    # ------------------------------------------------------------------ #
    # 序列接口（供策略 / 枚举器直接当列表使用）
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        """返回当前可见的数据长度（完整历史）。"""
        if self.table is None:
            return 0
        return self.table.size

    def __iter__(self) -> Iterator[RowView]:
        """迭代完整历史的行视图（不受 cursor 限制）。"""
        if self.table is None:
            return iter(())  # type: ignore[return-value]
        return self.table.iter_rows(0, self.table.size)

    def __getitem__(self, index: int) -> RowView:
        """
        支持正负索引访问（类似 list）。

        注意：这里访问的是完整历史中的索引，不受 cursor 限制。
        """
        if self.table is None:
            raise IndexError("TimeSeriesData is empty")

        size = self.table.size
        if index < 0:
            index += size
        if index < 0 or index >= size:
            raise IndexError(f"TimeSeriesData index out of range: {index}")
        return self.table.row_view(index)

    # ------------------------------------------------------------------ #
    # 数据装载
    # ------------------------------------------------------------------ #
    def attach_table(self, table: ColumnarTable, date_field: Optional[str] = None) -> None:
        """
        绑定已有 ColumnarTable 作为时序数据源。

        Args:
            table: 列式表
            date_field: 日期字段名（如果提供则覆盖自身的 date_field）
        """
        if date_field is not None:
            self.date_field = date_field

        if self.date_field not in table.headers:
            raise ValueError(
                f"TimeSeriesData.attach_table: date_field '{self.date_field}' "
                f"not found in headers: {table.headers}"
            )

        self.table = table
        self.cursor = -1

    def attach_rows(self, rows: List[Dict[str, Any]]) -> None:
        """
        从 List[Dict] 装载数据并构建内部 ColumnarTable。

        这是从 DB / DataSource / CSV 读出行式数据后的一次性转换入口。
        """
        if not rows:
            self.table = ColumnarTable(headers=[], columns={})
            self.cursor = -1
            return

        table = ColumnarTable.from_row_dicts(rows)
        self.attach_table(table, date_field=self.date_field)

    # ------------------------------------------------------------------ #
    # 游标控制
    # ------------------------------------------------------------------ #
    def advance_until(self, date_of_today: str) -> int:
        """
        推进游标直到指定日期（含）。

        假设 date_field 列已按升序排列，且比较基于字符串是安全的（YYYYMMDD）。

        Returns:
            新的 cursor 索引（-1 表示无数据）
        """
        if self.table is None or self.table.size == 0:
            self.cursor = -1
            return self.cursor

        dates = self.table.columns[self.date_field]
        i = self.cursor + 1
        n = self.table.size

        while i < n:
            d = dates[i]
            if d is None:
                i += 1
                continue
            if d > date_of_today:
                break
            i += 1

        self.cursor = i - 1
        return self.cursor

    def iter_until_cursor(self) -> Iterator[RowView]:
        """
        迭代 [0 .. cursor] 范围内的所有行视图。

        如果 cursor < 0 或 table 为空，则不返回任何行。
        """
        if self.table is None or self.cursor < 0:
            return iter(())  # type: ignore[return-value]
        return self.table.iter_rows(0, self.cursor + 1)

