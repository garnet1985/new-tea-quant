"""Database（``infra.db``）— 数据库基础设施。

公开门面::

    from core.infra.db import Db

跨模块契约（表模型等）优先::

    from core.infra.db.contracts import DbBaseModel, Field, DatabaseManager

为兼容 userspace / 脚手架里常见的短导入，也从本包再导出 ``DbBaseModel`` 等契约符号。
"""

from .contracts import DatabaseManager, DbBaseModel, Field
from .db import Db

__all__ = ["Db", "DbBaseModel", "Field", "DatabaseManager"]
