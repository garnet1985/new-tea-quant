"""
DbTableAbc — 单表 CRUD 契约；各 backend 的 TableOperator 实现本 ABC。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class DbTableAbc(ABC):
    """
    表级操作抽象基类。

    通过 ``DbEngineAbc.table_operator(table_name)`` 获取实例。
    业务层 ``DbBaseModel`` 持有并转发本接口，不继承 ABC。
    """

    @property
    @abstractmethod
    def table_name(self) -> str:
        """绑定的物理表名。"""
        pass

    # ------------------------------------------------------------------
    # Read（abstract）
    # ------------------------------------------------------------------

    @abstractmethod
    def load(
        self,
        condition: str = "1=1",
        params: tuple = (),
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """按条件查询；须支持 limit / offset 以防 OOM。"""
        pass

    @abstractmethod
    def query(self, sql: str, params: Any = None) -> List[Dict[str, Any]]:
        """参数化读查询（同域 JOIN 等）。"""
        pass

    # ------------------------------------------------------------------
    # Write（abstract）
    # ------------------------------------------------------------------

    @abstractmethod
    def insert(
        self,
        rows: List[Dict[str, Any]],
        unique_keys: Optional[List[str]] = None,
    ) -> int:
        """同步插入（1 行或多行）；DuckDB 经底层写 queue + wait。"""
        pass

    @abstractmethod
    def upsert(self, rows: List[Dict[str, Any]], unique_keys: List[str]) -> int:
        """同步 upsert（INSERT … ON CONFLICT …）。"""
        pass

    @abstractmethod
    def delete(
        self,
        condition: str,
        params: tuple = (),
        limit: Optional[int] = None,
    ) -> int:
        """按条件删除。"""
        pass

    # ------------------------------------------------------------------
    # Other（abstract）
    # ------------------------------------------------------------------

    @abstractmethod
    def count(self, condition: str = "1=1", params: tuple = ()) -> int:
        """条件计数。"""
        pass

    # ------------------------------------------------------------------
    # Meta（abstract）
    # ------------------------------------------------------------------

    @abstractmethod
    def load_schema(self) -> Dict[str, Any]:
        """加载本表 schema dict。"""
        pass

    # ------------------------------------------------------------------
    # Concrete defaults（三 backend 共享，子类无需覆写）
    # ------------------------------------------------------------------

    def load_one(
        self,
        condition: str = "1=1",
        params: tuple = (),
        order_by: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        rows = self.load(condition, params, order_by=order_by, limit=1)
        return rows[0] if rows else None

    def is_exists(self, condition: str, params: tuple = ()) -> bool:
        return self.count(condition, params) > 0

    def is_empty(self) -> bool:
        return self.count("1=1", ()) == 0

    def insert_many(
        self,
        rows: List[Dict[str, Any]],
        unique_keys: Optional[List[str]] = None,
    ) -> int:
        return self.insert(rows, unique_keys)

    def upsert_many(self, rows: List[Dict[str, Any]], unique_keys: List[str]) -> int:
        return self.upsert(rows, unique_keys)

    def replace(self, rows: List[Dict[str, Any]], unique_keys: List[str]) -> int:
        """MongoDB replace 语义：冲突时整行替换 → 等同 upsert。"""
        return self.upsert(rows, unique_keys)
