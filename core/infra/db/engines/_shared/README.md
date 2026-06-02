# `_shared/` — 仅放可选 helper

**不放** engine 编排、connector、table_operator、batch write 或任何 `engine_key` 分支。

新同学改 MySQL → `engines/mysql/`；改 PostgreSQL → `engines/pgsql/`；改 DuckDB → `engines/duckdb/`。

允许示例：与方言无关的纯函数、测试 fixture（须满足 `ARCHITECTURE.md` §6）。

已落地：

- `fields/` — 跨 backend 字段类型定义（`Field.from_dict`）
- `schema_parser_base.py` / `ddl_executor.py` / `schema_introspection.py` — DDL 与列 introspection
- `config_parse.py` — `database.json` 校验与默认值
- `dialect.py` / `sql_identifiers.py` — 方言、标识符引用
- `row_sql.py` — 行数据 → INSERT/UPSERT 片段、NaN 清洗
- `cursor.py` / `query_executor.py` — 同步游标与 connector 协议
- `batch_write_settings.py` — mysql/pgsql 写队列配置
