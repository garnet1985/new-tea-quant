"""
DbQueryExecutor — DatabaseCursor 所需的 execute_query / execute_write 协议。

由 mysql / pgsql / duckdb connector 实现。
"""
from __future__ import annotations

from typing import Any, Dict, List, Protocol


class DbQueryExecutor(Protocol):
    def execute_query(self, query: str, params: Any = None) -> List[Dict[str, Any]]:
        ...

    def execute_write(self, query: str, params: Any = None) -> int:
        ...
