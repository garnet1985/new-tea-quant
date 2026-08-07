"""通用游标包装：统一 dict 结果与读写分流。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.infra.db.core.engines.shared.query_executor import DbQueryExecutor


class DatabaseCursor:
    """
    统一游标：封装 ``DbQueryExecutor`` 的读写分流。

    写操作在 execute 时立即执行；读操作在 fetchall 时执行。
    """

    def __init__(self, executor: DbQueryExecutor):
        self.adapter = executor
        self._cursor = None
        self._result = None
        self._rowcount = 0

    @staticmethod
    def _is_write_query(query: str) -> bool:
        q = query.strip().upper()
        return q.startswith(
            ("INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "TRUNCATE")
        )

    def execute(self, query: str, params: Any = None):
        self._query = query
        self._params = params
        self._result = None
        self._rowcount = 0
        if self._is_write_query(query):
            self._rowcount = self.adapter.execute_write(query, params)
        return self

    def fetchall(self) -> List[Dict[str, Any]]:
        if not hasattr(self, "_query"):
            return []
        self._result = self.adapter.execute_query(self._query, self._params)
        return self._result

    def fetchone(self) -> Optional[Dict[str, Any]]:
        results = self.fetchall()
        return results[0] if results else None

    @property
    def rowcount(self) -> int:
        if self._result is not None:
            return len(self._result)
        return getattr(self, "_rowcount", 0)

    def close(self):
        pass
