#!/usr/bin/env python3
"""
列式数据结构（Columnar Data Classes）

设计目标：
- 在内存中以列式方式承载表格/时序数据，减少 List[Dict] 带来的内存与 CPU 开销
- 为策略、模拟器等上层组件提供统一的行视图（RowView），对调用方尽量“像 dict 一样好用”
- 不依赖 pandas / numpy / pyarrow，后续可以在内部透明替换为更高效的实现
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, List, Mapping, MutableMapping, Optional
from collections.abc import Mapping as ABCMapping


class RowView(ABCMapping):
    """
    单行只读视图。

    - 背后引用 ColumnarTable，不复制任何数据
    - 支持 dict 常用访问模式：row["field"], row.get("field"), for k in row.keys()
    - 如需真正的 dict，可显式调用 dict(row) 或 row.to_dict()
    """

    __slots__ = ("_table", "_index")

    def __init__(self, table: "ColumnarTable", index: int) -> None:
        self._table = table
        self._index = index

    # --- Mapping 接口 --------------------------------------------------------
    def __getitem__(self, key: str) -> Any:  # type: ignore[override]
        try:
            column = self._table.columns[key]
        except KeyError:
            raise KeyError(key) from None
        idx = self._index
        if idx < 0 or idx >= len(column):
            raise IndexError(f"row index out of range: {idx}")
        return column[idx]

    def __iter__(self) -> Iterator[str]:  # type: ignore[override]
        return iter(self._table.headers)

    def __len__(self) -> int:  # type: ignore[override]
        return len(self._table.headers)

    # --- 便捷方法 -----------------------------------------------------------
    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self) -> Iterable[str]:  # type: ignore[override]
        return self._table.headers

    def to_dict(self) -> Dict[str, Any]:
        """将当前行 materialize 为普通 dict。"""
        return {k: self[k] for k in self._table.headers}

    # 表示与调试
    def __repr__(self) -> str:
        preview = ", ".join(f"{k}={self.get(k)!r}" for k in self._table.headers[:5])
        if len(self._table.headers) > 5:
            preview += ", ..."
        return f"<RowView idx={self._index} {preview}>"


@dataclass
class ColumnarTable:
    """
    通用列式表结构。

    - headers: 字段名列表（列顺序）
    - columns: 字段名 -> 列数据（list），所有列长度一致
    """

    headers: List[str]
    columns: Dict[str, List[Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # 规范化 headers：去重并保持顺序
        seen = set()
        unique_headers: List[str] = []
        for h in self.headers:
            if h not in seen:
                seen.add(h)
                unique_headers.append(h)
        self.headers = unique_headers

        # 确保 columns 至少包含 headers 中出现的键
        for h in self.headers:
            self.columns.setdefault(h, [])

        # 校验所有列长度一致
        lengths = {len(col) for col in self.columns.values()}
        if len(lengths) > 1:
            raise ValueError(
                f"Inconsistent column lengths in ColumnarTable: {lengths}"
            )

    # ------------------------------------------------------------------ #
    # 基本属性与访问
    # ------------------------------------------------------------------ #
    @property
    def size(self) -> int:
        """行数。"""
        if not self.columns:
            return 0
        # 任取一列
        first_col = next(iter(self.columns.values()))
        return len(first_col)

    def get_column(self, name: str) -> List[Any]:
        """获取某一列（原始 list）。"""
        return self.columns[name]

    # ------------------------------------------------------------------ #
    # 行视图
    # ------------------------------------------------------------------ #
    def row_view(self, index: int) -> RowView:
        """获取单行 RowView（不复制数据）。"""
        if index < 0 or index >= self.size:
            raise IndexError(f"row index out of range: {index}")
        return RowView(self, index)

    def iter_rows(self, start: int = 0, end: Optional[int] = None) -> Iterator[RowView]:
        """
        按区间迭代行视图 [start, end)。
        """
        if end is None or end > self.size:
            end = self.size
        if start < 0:
            start = 0
        for idx in range(start, end):
            yield RowView(self, idx)

    # ------------------------------------------------------------------ #
    # 构造辅助方法
    # ------------------------------------------------------------------ #
    @classmethod
    def from_row_dicts(cls, rows: List[Dict[str, Any]]) -> "ColumnarTable":
        """
        从 List[Dict] 构建 ColumnarTable。

        注意：这是一个 O(N * K) 的一次性转换，适合在读 DB/CSV 后尽快完成，
        避免在核心模拟循环中频繁操作 dict。
        """
        if not rows:
            return cls(headers=[], columns={})

        # 收集所有出现过的字段名，保持顺序
        headers: List[str] = []
        seen = set()
        for row in rows:
            for k in row.keys():
                if k not in seen:
                    seen.add(k)
                    headers.append(k)

        columns: Dict[str, List[Any]] = {h: [] for h in headers}
        for row in rows:
            for h in headers:
                columns[h].append(row.get(h))

        return cls(headers=headers, columns=columns)


