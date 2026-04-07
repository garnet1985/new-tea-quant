"""
Database Helpers - 数据库辅助工具模块

提供静态类或纯业务无关的操作：
- 数据库操作辅助（数据转换、NaN 清理、配置解析等）
- 游标包装

MySQL / PostgreSQL / SQLite 的标识符引用等方言差异，请统一使用
:class:`DBHelper` 的 ``quote_identifier`` / ``quote_identifier_for_dialect`` /
``quote_identifier_list``；业务与 userspace 不必直接依赖 ``sql_identifiers``。
"""
from .db_helpers import DBHelper, DatabaseCursor

__all__ = [
    "DBHelper",
    "DatabaseCursor",
]
