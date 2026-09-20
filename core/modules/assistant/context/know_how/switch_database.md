---
title: switch database 切换数据库
aliases:
  - database
  - duckdb
  - mysql
  - postgresql
  - 换库
  - 数据库
  - 切换数据库
summary: 在设置里改数据库类型；MySQL/PostgreSQL 还要改连接文件，重启后生效。
---

# 如何切换数据库

NTQ 默认用 DuckDB（三个本地文件）。同一套表结构也支持 MySQL / PostgreSQL。换库**只改配置**，不会自动把旧库里的行情搬过去。

## 前置条件

- 已经完成安装，存在 `userspace/system/config/database/`
- 若选 MySQL / PostgreSQL：本机已能连上对应服务，库不存在时程序会尝试新建

## 在界面里改类型

1. 打开 **设置 → 数据库**
2. 选类型：`DuckDB`（推荐，本地文件） / `PostgreSQL` / `MySQL`
3. 选 PostgreSQL 或 MySQL 时填写**库名**（字母、数字、下划线、连字符、点）
4. 点 **保存数据库设置**
5. **关掉再打开** `python launcher.py`（保存文案会提示重启后生效）

界面改的是 `userspace/system/config/database/common.json` 里的 `database_type`。

## 连接参数（MySQL / PostgreSQL）

类型保存后，还要改对应 json 里的 host / port / user / password：

| 类型 | 文件 |
| --- | --- |
| DuckDB | `userspace/system/config/database/duckdb.json` |
| MySQL | `userspace/system/config/database/mysql.json` |
| PostgreSQL | `userspace/system/config/database/postgresql.json` |

环境变量可覆盖连接：`DB_HOST`、`DB_PORT`、`DB_USER`、`DB_PASSWORD`。不要把密码提交进 git。

DuckDB 三个文件默认在 `userspace/system/db/`：`data.duckdb`（行情）、`tag.duckdb`（标签）、`strategy.duckdb`（回测产物）。高级参数直接编辑 `duckdb.json`。

## 验证

- 设置页重新读取后，类型与库名与刚才保存的一致
- 能打开制定策略并跑一步枚举（或 `python cli.py se --strategy random_v1`）而不报连库失败

## 常见坑

- **换类型不会迁移数据。** 新库是空的，需要再导入演示包（`python cli.py id`）或自己的数据源。
- **想并存 demo 与全量数据：** 给 PostgreSQL / MySQL 换一个库名，或给 DuckDB 改 `duckdb.json` 里的文件名。
- **开发时 DuckDB 单写模式**不适合多进程抢同一个文件；多人/多进程调试更适合 MySQL / PostgreSQL。
- 表结构由框架建，不要手改 `sys_` 内置表。

概念见 [数据基建](../wiki/data_infrastructure.md)。
