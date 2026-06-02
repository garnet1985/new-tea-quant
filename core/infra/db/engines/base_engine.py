"""
BaseDatabaseEngine - 三种数据库后端的统一抽象

⚠️ 草案，未采纳。定案架构见同目录 ARCHITECTURE.md 与 docs/DECISIONS.md 决策 7、8。
   目标方向：无胖基类；duckdb/mysql/pgsql 平级包 + engine 编排子模块。

================================================================================
职责边界（Review 用）
================================================================================

【DatabaseManager 负责（外层）】
  - 读取 userspace/system/config/database，解析为 EngineConfigMeta
  - 按 meta.engine_key 选择并构造具体 Engine 实例
  - 对外暴露 database_type / is_duckdb 等业务判断（若上层需要）
  - 协调 SchemaManager、StorageRegistry、TableManager

【Engine 负责（本抽象类及子类）】
  - 仅消费传入的 meta，不向外声明「我是 duckdb/mysql」
  - 连接生命周期、读/写、按表路由（子类内部实现差异）
  - 子类私有：写管道、IPC、多进程 hook 等

【Engine 不负责】
  - 读配置文件、合并 common.json + backend json
  - Schema / migrate / 业务 SQL
  - 用 is_duckdb 等标志驱动上层分支（该逻辑留在 Manager 或更外层）

构造约定::

    meta = manager.build_engine_meta()   # Manager 解析配置
    engine = create_engine(meta)         # 工厂按 meta.engine_key 选型
    engine.initialize(context)           # 绑定运行时上下文（含表→域解析等）

================================================================================
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.infra.db.table_queriers.adapters.base_adapter import BaseDatabaseAdapter


# ---------------------------------------------------------------------------
# Manager → Engine 的配置 meta（Review：字段是否够用）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EngineConfigMeta:
    """
    DatabaseManager 解析 db 配置后传入 Engine 的元信息。

    Engine 只读此对象，不回写 database_type 给上层做业务分支。
    """

    engine_key: str
    """工厂选型键：mysql | postgresql | duckdb"""

    raw_config: Dict[str, Any] = field(default_factory=dict)
    """parse 后的完整 db 配置（含 database_type 与各 backend 块）"""

    backend_config: Dict[str, Any] = field(default_factory=dict)
    """当前 backend 专属块：mysql / postgresql / duckdb"""

    options: Dict[str, Any] = field(default_factory=dict)
    """可选能力开关（由 Manager 从配置合并，如 batch_write、verbose 相关项）"""


@dataclass
class EngineRuntimeContext:
    """
    initialize() 时由 DatabaseManager 注入的运行时上下文。

    表→域映射等「编排信息」由 Manager 持有；Engine 通过回调访问，避免 Engine 依赖 StorageRegistry。
    """

    resolve_table_domain: Callable[[str], str]
    """table_name → storage_domain"""

    resolve_table_adapter: Callable[[str], "BaseDatabaseAdapter"]
    """table_name → 适配器（占位符、execute_batch）"""


class BaseDatabaseEngine(ABC):
    """
    数据库 Engine 基类。

    子类：MySQLEngine | PostgreSQLEngine | DuckDBEngine
    实例化只接收 EngineConfigMeta；业务侧类型判断在 DatabaseManager。
    """

    def __init__(self, meta: EngineConfigMeta, *, is_verbose: bool = False) -> None:
        self.meta = meta
        self.is_verbose = is_verbose
        self._context: Optional[EngineRuntimeContext] = None
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Engine 是否已完成 initialize。"""
        return self._initialized


    # ------------------------------------------------------------------
    # 1. 生命周期
    # ------------------------------------------------------------------

    @abstractmethod
    def initialize(self, context: EngineRuntimeContext) -> None:
        """
        建立连接层，启动写管道 / IPC 等（子类按需）。

        调用方：DatabaseManager.initialize()
        """
        pass


    @abstractmethod
    def connect(self) -> None:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def create_table(self, table_name: str) -> None:
        pass

    @abstractmethod
    def drop_table(self, table_name: str) -> None:
        pass

    @abstractmethod
    def create_tables(self, table_names: List[str]) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        """释放 Engine 私有资源。调用方：DatabaseManager.close()"""
        pass




    # ------------------------------------------------------------------
    # 2. 运行时能力（中性命名，不含 is_duckdb）
    # ------------------------------------------------------------------

    @abstractmethod
    def can_run_ddl_in_current_process(self) -> bool:
        """
        当前 OS 进程是否允许执行 CREATE TABLE 等 DDL。

        由 Engine 根据自身的连接/进程模型决定；Manager 只问结果，不 if backend 类型。

        调用方：create_all_base_tables / register_table
        """
        pass

    @contextmanager
    def worker_pool_scope(self):
        """
        多进程 worker 池整段执行的前后置（上下文管理器）。

        需要特殊处理的 Engine 覆盖；默认 no-op。
        调用方：ProcessWorker.run_jobs（由 Manager 决定是否包裹）
        """
        yield

    # ------------------------------------------------------------------
    # 3. 连接 / 适配器（建表、exists 检查）
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def primary_adapter(self) -> Optional["BaseDatabaseAdapter"]:
        """主连接适配器（各 backend 语义由子类定义）。"""
        pass

    @abstractmethod
    def connection_factory_for_table(self, table_name: str) -> Callable:
        """
        SchemaManager 建表用连接工厂。

        签名：@contextmanager def get_connection(): yield conn
        """
        pass

    # ------------------------------------------------------------------
    # 4. 读路径
    # ------------------------------------------------------------------

    @abstractmethod
    def get_connection(self, *, scope: Optional[str] = None):
        """
        原生连接（上下文管理器）。

        scope：可选路由键（如 storage_domain）；单库 Engine 可忽略。
        """
        pass

    @abstractmethod
    def get_sync_cursor(self, *, scope: Optional[str] = None):
        """DatabaseCursor（上下文管理器）。"""
        pass

    @abstractmethod
    def get_sync_cursor_for_table(self, table_name: str):
        """按表路由后的游标。DbBaseModel 读/DDL 主入口。"""
        pass

    @abstractmethod
    def transaction(self, *, scope: Optional[str] = None):
        """事务游标（上下文管理器）。"""
        pass

    @abstractmethod
    def transaction_for_table(self, table_name: str):
        """按表路由后的事务。DbBaseModel 事务主入口。"""
        pass

    @abstractmethod
    def execute_sync_query(
        self,
        query: str,
        params: Any = None,
        *,
        scope: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        同步查询。

        scope：可选路由键；跨表 SQL 且已知 scope 时使用。
        """
        pass

    @abstractmethod
    def execute_sync_query_for_table(
        self,
        table_name: str,
        query: str,
        params: Any = None,
    ) -> List[Dict[str, Any]]:
        """按表名路由后查询。DbBaseModel._table_query 主入口。"""
        pass

    # ------------------------------------------------------------------
    # 5. 写路径
    # ------------------------------------------------------------------

    @abstractmethod
    def queue_write(
        self,
        table_name: str,
        data_list: List[Dict[str, Any]],
        unique_keys: List[str],
        callback: Optional[Callable] = None,
    ) -> None:
        """异步入队批量写。"""
        pass

    @abstractmethod
    def write_rows_sync(
        self,
        table_name: str,
        data_list: List[Dict[str, Any]],
        unique_keys: List[str],
    ) -> int:
        """同步批量写，返回写入行数。"""
        pass

    @abstractmethod
    def flush_writes(self, table_name: Optional[str] = None) -> None:
        """刷写待写入队列。"""
        pass

    @abstractmethod
    def wait_for_writes(self, timeout: float = 30.0) -> None:
        """等待异步写完成。"""
        pass

    @abstractmethod
    def get_write_stats(self) -> Dict[str, Any]:
        """写队列 / 管道统计。"""
        pass

    # ------------------------------------------------------------------
    # 6. 运维 / 观测
    # ------------------------------------------------------------------

    @abstractmethod
    def get_engine_stats(self) -> Dict[str, Any]:
        """Engine 级统计；由 DatabaseManager.get_stats() 合并。"""
        pass

    # ------------------------------------------------------------------
    # 子类内部辅助
    # ------------------------------------------------------------------

    def _require_initialized(self) -> EngineRuntimeContext:
        if not self._initialized or self._context is None:
            raise RuntimeError(
                f"{type(self).__name__} 未 initialize，请先通过 DatabaseManager 初始化"
            )
        return self._context

    def _resolve_domain(self, table_name: str) -> str:
        return self._require_initialized().resolve_table_domain(table_name)
