"""
SQL 标识符引用（实现细节）。

对外请使用 :class:`core.infra.db.helpers.db_helpers.DBHelper` 的
``quote_identifier`` / ``quote_identifier_for_dialect`` / ``quote_identifier_list``，
不要在 userspace 中直接依赖本模块。
"""
from __future__ import annotations


def quote_ddl_identifier(database_type: str, name: str) -> str:
    """
    为 DDL 引用标识符。

    - ``mysql``：反引号 `` `name` ``（MariaDB 同）。
    - ``postgresql`` / ``sqlite``：双引号 ``"name"``。

    Args:
        database_type: ``postgresql`` | ``mysql`` | ``sqlite`` 等。
        name: 表名、列名或索引名；``None`` 原样返回。

    Returns:
        引用后的标识符字符串。
    """
    if name is None:
        return name
    s = str(name)
    if database_type == "mysql":
        return "`" + s.replace("`", "``") + "`"
    return '"' + s.replace('"', '""') + '"'
