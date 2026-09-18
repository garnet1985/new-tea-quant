---
title: NTQ 的数据基建
aliases:
  - db
  - data manager
  - database
  - infrastructure
  - data distribution
summary: NTQ的数据库管理与数据分发服务简介
---

# 数据基础设施：db 与 data\_manager

## 两个模块的职责

| 模块                     | 门面                | 职责                                               |
| ---------------------- | ----------------- | ------------------------------------------------ |
| `infra/db`             | `DatabaseManager` | 数据库连接、schema 管理、表初始化、物理表名映射                      |
| `modules/data_manager` | `DataManager`     | 统一数据访问门面、领域服务（stock/macro/calendar/index）、表发现与注册 |

## 为什么分两层

- **db 是基础设施**：不认识股票、策略、标签这些概念，只管连接池、schema、DuckDB/MySQL/PostgreSQL 的差异

- **data\_manager 是领域层**：认识股票、指数、宏观这些领域，提供 `dm.stock.kline.load(...)` 这种领域 API

简单说：db 管"怎么连数据库"，data\_manager 管"怎么查股票数据"。

## db 模块

### 三存储域

DuckDB 模式下有三个数据库文件：

| 域        | 文件                | 内容         |
| -------- | ----------------- | ---------- |
| data     | `data.duckdb`     | 行情、财务、宏观数据 |
| tag      | `tag.duckdb`      | 标签计算结果     |
| strategy | `strategy.duckdb` | 策略回测产物     |

### 多后端

同一个 `schema.py` 在 DuckDB / MySQL / PostgreSQL 下都能建表。用户换数据库只改配置文件，代码不动。

### 环境变量覆盖

`DB_HOST`、`DB_PORT`、`DB_USER`、`DB_PASSWORD` 可以覆盖配置文件中的连接参数。

## data\_manager 模块

### 表发现

`DataManager` 初始化时自动发现表：

1. 扫描 `core/tables/`（内置表，必须 `sys_` 前缀）
2. 扫描 `userspace/extensions/tables/`（用户自定义表，名称任意）
3. 每个表目录下的 `schema.py` 定义表结构
4. 可选的 `model.py` 定义数据操作类

### 领域服务

通过属性链访问：

```python
dm = DataManager()
dm.stock.kline.load("000001.SZ", term="daily", start_date="20240101")
dm.macro.load_gdp()
dm.calendar.load_trading_dates()
```

| 服务         | 职责        |
| ---------- | --------- |
| `stock`    | 股票行情、财务数据 |
| `index`    | 指数数据      |
| `macro`    | 宏观经济数据    |
| `calendar` | 交易日历      |

### 样本股票宇宙

`use_sample_stock_list`（在 `data.json` 中配置）决定系统保留哪些股票。开发时用 300 只样本，正式回测跑全量。

### 单例

`DataManager` 默认进程内单例（锁 + 双重检查）。多进程时每进程各自一个实例。

## 与 data\_contract 的边界

| 模块              | 职责                                |
| --------------- | --------------------------------- |
| `data_manager`  | 表的 CRUD、领域查询、Model 实例化            |
| `data_contract` | DataKey 白名单、契约签发、loader 取数、时序 PIT |

data\_manager 管物理表的读写，data\_contract 管数据依赖的声明和签发。策略钩子里 `ctx.data("stock.kline.daily")` 走的是 data\_contract，不是直接调 data\_manager。
