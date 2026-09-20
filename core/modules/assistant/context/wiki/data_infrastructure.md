---
title: NTQ 的数据基建
aliases:
  - db
  - data manager
  - database
  - 数据库
  - 数据基建
  - 换库
summary: 数据库怎么连、股票数据从哪查；换库只改配置。
---

# 数据基建

两层分工：

| 层 | 职责 |
| --- | --- |
| 数据库 | 连接、schema、建表。不认识股票或策略 |
| 数据访问 | 按领域查数：股票 / 宏观 / 日历 / 指数 |

换库只改配置，代码不动。操作步骤见 [切换数据库](../know_how/switch_database.md)。策略钩子里用 `ctx.data.items_with_meta()` 按数据键取数，不要自己连库。

## DuckDB 三个文件

| 域 | 文件 | 内容 |
| --- | --- | --- |
| data | `data.duckdb` | 行情、财务、宏观 |
| tag | `tag.duckdb` | 标签结果 |
| strategy | `strategy.duckdb` | 回测产物 |

默认在 `userspace/system/db/`。MySQL / PostgreSQL 用同一套表结构。`DB_HOST`、`DB_PORT`、`DB_USER`、`DB_PASSWORD` 可覆盖配置文件。

## 表从哪来

1. `core/tables/`：内置表，必须 `sys_` 前缀
2. `userspace/extensions/tables/`：自定义表，名称任意
3. 每个表目录有 `schema.py`，可选 `model.py`

## 领域查询（框架内部）

数据访问按领域挂服务：股票行情/财务、指数、宏观、交易日历。开发时可用 `data.json` 的 `use_sample_stock_list` 只留约 300 只样本，正式回测再跑全量。

策略不要直接调数据访问层；数据契约负责按键加载，底层再去查表。
