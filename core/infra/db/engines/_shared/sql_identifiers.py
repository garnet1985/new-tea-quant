"""DDL/DML 标识符引用（按方言）。"""
from __future__ import annotations


def quote_ddl_identifier(database_type: str, name: str) -> str:
    """
    为 DDL 引用标识符。

    - ``mysql``：反引号 `` `name` ``（MariaDB 同）。
    - ``postgresql`` / ``duckdb``：双引号 ``"name"``。
    """
    if name is None:
        return name
    s = str(name)
    if database_type in ("postgresql", "duckdb"):
        return f'"{name}"'
    if database_type == "mysql":
        return "`" + s.replace("`", "``") + "`"
    return '"' + s.replace('"', '""') + '"'
