# `_shared/` — 仅放可选 helper

**不放** engine 编排、connector、table_operator、batch write 或任何 `engine_key` 分支。

新同学改 MySQL → `engines/mysql/`；改 PostgreSQL → `engines/pgsql/`；改 DuckDB → `engines/duckdb/`。

允许示例：与方言无关的纯函数、测试 fixture（须满足 `ARCHITECTURE.md` §6）。
