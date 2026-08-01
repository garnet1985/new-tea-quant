"""跨模块契约类型与常用符号（表模型、字段、Engine 抽象等）。

推荐::

    from core.infra.db.contracts import DbBaseModel, Field, DatabaseManager

过渡期包根 ``__init__`` 仍 re-export 下列符号，后续将收紧为仅 ``Db``。
"""

from __future__ import annotations

from core.infra.db.core.db_manager import DatabaseManager
from core.infra.db.core.engines import (
    DbEngineAbc,
    DbTableAbc,
    EngineConfigMeta,
    build_engine_meta,
    create_engine,
)
from core.infra.db.core.engines.shared.fields import Field
from core.infra.db.core.storage_registry import STORAGE_DOMAINS, StorageRegistry
from core.infra.db.core.table_queriers.db_base_model import DbBaseModel
from core.infra.db.core.table_queriers.services import BatchOperation, BatchWriteQueue

__all__ = [
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
