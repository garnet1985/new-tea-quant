from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Hashable, List, Mapping, Optional

from core.modules.data_contract.contracts import DataContract

from .data_cursor import DataCursor


@dataclass
class DataCursorManager:
    """轻量级 DataCursor 注册与调度器（按名称管理会话）。"""

    _cursors: Dict[str, DataCursor] = field(default_factory=dict)

    def create_cursor(
        self,
        name: str,
        contracts: Mapping[Hashable, DataContract],
        *,
        time_field_overrides: Optional[Mapping[Hashable, Optional[str]]] = None,
    ) -> DataCursor:
        cursor = DataCursor(
            contracts=contracts,
            time_field_overrides=time_field_overrides,
        )
        self._cursors[name] = cursor
        return cursor

    def create_cursor_from_rows(
        self,
        name: str,
        rows_by_source: Mapping[Hashable, List[Dict[str, Any]]],
        *,
        time_field_overrides: Optional[Mapping[Hashable, Optional[str]]] = None,
    ) -> DataCursor:
        """用行式数据直接创建 cursor（适配 strategy 当前数据结构）。"""
        cursor = DataCursor.from_rows(
            rows_by_source=rows_by_source,
            time_field_overrides=time_field_overrides,
        )
        self._cursors[name] = cursor
        return cursor

    def get_cursor(self, name: str) -> DataCursor:
        cursor = self._cursors.get(name)
        if cursor is None:
            raise KeyError(f"未找到 cursor: {name}")
        return cursor

    def reset_cursor(self, name: str) -> None:
        self.get_cursor(name).reset()

    def drop_cursor(self, name: str) -> None:
        self._cursors.pop(name, None)
