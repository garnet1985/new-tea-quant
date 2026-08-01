"""跨模块契约类型与常用符号（表模型、字段、Engine 抽象等）。

仅导出类型 / 类 / 常量；行为入口见门面 ``Db``::

    from core.infra.db import Db
    from core.infra.db.contracts import DbBaseModel, Field, DatabaseManager
"""

from __future__ import annotations

from core.infra.db.core.db_manager import DatabaseManager
from core.infra.db.core.engines import (
    DbEngineAbc,
    DbTableAbc,
    EngineConfigMeta,
)
from core.infra.db.core.engines.shared.fields import Field
from core.infra.db.core.schema_manager import SchemaManager
from core.infra.db.core.storage_registry import STORAGE_DOMAINS, StorageRegistry
from core.infra.db.core.table_queriers.db_base_model import DbBaseModel
from core.infra.db.core.table_queriers.services import BatchOperation, BatchWriteQueue

__all__ = [
    "DatabaseManager",
    "SchemaManager",
    "StorageRegistry",
    "STORAGE_DOMAINS",
    "DbEngineAbc",
    "DbTableAbc",
    "EngineConfigMeta",
    "DbBaseModel",
    "Field",
    "BatchOperation",
    "BatchWriteQueue",
]
