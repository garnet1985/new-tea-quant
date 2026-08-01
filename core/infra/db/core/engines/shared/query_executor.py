"""
DbQueryExecutor — DatabaseCursor 所需的 execute_query / execute_write 协议。

由 mysql / pgsql / duckdb connector 实现。

读查询返回的 dict 行须经 ``query_rows.normalize_query_rows`` 规范化
（DECIMAL→float、numpy 标量→原生类型等），保证上层只见可安全混算的类型。
"""
from __future__ import annotations

from typing import Any, Dict, List, Protocol


class DbQueryExecutor(Protocol):
    def execute_query(self, query: str, params: Any = None) -> List[Dict[str, Any]]:
        ...

    def execute_write(self, query: str, params: Any = None) -> int:
        ...
