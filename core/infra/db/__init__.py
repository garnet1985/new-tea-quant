"""Database（``infra.db``）— 数据库基础设施。

公开门面::

    from core.infra.db import Db

跨模块契约（表模型等）::

    from core.infra.db.contracts import DbBaseModel, Field, DatabaseManager

**过渡期：** 为兼容存量 ``from core.infra.db import DatabaseManager`` 等写法，
包根仍 re-export ``contracts`` 中的符号。后续调用方迁移完成后将只保留 ``Db``。
"""

from .contracts import (
    STORAGE_DOMAINS,
    BatchOperation,
    BatchWriteQueue,
    DatabaseManager,
    DbBaseModel,
    DbEngineAbc,
    DbTableAbc,
    EngineConfigMeta,
    Field,
    StorageRegistry,
    build_engine_meta,
    create_engine,
)
from .db import Db

__all__ = [
    "Db",
    # --- transitional re-exports (migrate callers to Db / contracts) ---
    "DatabaseManager",
    "StorageRegistry",
    "STORAGE_DOMAINS",
    "DbEngineAbc",
    "DbTableAbc",
    "EngineConfigMeta",
    "build_engine_meta",
    "create_engine",
    "DbBaseModel",
    "Field",
    "BatchOperation",
    "BatchWriteQueue",
]
