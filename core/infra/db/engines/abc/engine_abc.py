"""
DbEngineAbc — 挂载在 DatabaseManager 上的引擎契约。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.infra.db.engines.abc.table_abc import DbTableAbc
    from core.infra.db.engines.meta import EngineConfigMeta


class DbEngineAbc(ABC):
    """
    数据库 Engine 抽象基类。

    DatabaseManager 按配置 mount 唯一实例：``manager.engine``。
    单表 CRUD 通过 ``table_operator(table_name)`` 获取 ``DbTableAbc`` 实现。
    """

    def __init__(self, meta: "EngineConfigMeta", *, is_verbose: bool = False) -> None:
        self.meta = meta
        self.is_verbose = is_verbose
        self._initialized = False
        self._table_operator_cache: Dict[str, "DbTableAbc"] = {}

    @property
    def engine_key(self) -> str:
        return self.meta.engine_key

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    def initialize(self) -> None:
        """建立连接 / 文件 / 写管道等。"""
        pass

    @abstractmethod
    def close(self) -> None:
        """释放 Engine 资源。"""
        pass

    # ------------------------------------------------------------------
    # Table operator factory
    # ------------------------------------------------------------------

    @abstractmethod
    def table_operator(self, table_name: str) -> "DbTableAbc":
        """
        返回绑定 ``table_name`` 的表级操作对象（TableOperator）。

        同一表名可缓存实例；须线程安全由各 backend 自行保证。
        """
        pass

    # ------------------------------------------------------------------
    # Storage & DDL（Engine 级，非 Table ABC）
    # ------------------------------------------------------------------

    @abstractmethod
    def ensure_storage(self) -> None:
        """确保库/文件存在（原 create_db）。"""
        pass

    @abstractmethod
    def create_table(self, schema: Dict[str, Any]) -> None:
        """按 schema 建单表及索引。"""
        pass

    @abstractmethod
    def create_all_tables(self, schemas: Dict[str, Dict[str, Any]]) -> None:
        """批量建表。"""
        pass

    @abstractmethod
    def table_exists(self, table_name: str) -> bool:
        pass

    @abstractmethod
    def drop_table(self, table_name: str) -> None:
        pass

    # ------------------------------------------------------------------
    # Write pipeline control
    # ------------------------------------------------------------------

    @abstractmethod
    def flush_writes(self, table_name: Optional[str] = None) -> None:
        """刷写异步/队列中的待写入数据。"""
        pass

    @abstractmethod
    def wait_for_writes(self, timeout: float = 30.0) -> None:
        pass

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        pass
