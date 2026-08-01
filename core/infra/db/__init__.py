"""Database（``infra.db``）— 数据库基础设施。

公开门面::

    from core.infra.db import Db

跨模块契约（表模型等）::

    from core.infra.db.contracts import DbBaseModel, Field, DatabaseManager
"""

from .db import Db

__all__ = ["Db"]
