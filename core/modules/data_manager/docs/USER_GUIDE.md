# Data Manager — 用户指南

**模块：** `modules.data_manager` · **版本：** `0.2.3`

**最低支持核心版本：** `>=0.5.0`

`DataManager 是本地数据的统一入口——查 K 线、查股票列表、查行业都从这里走。`
相关：[README.md](../README.md) · [API.md](../API.md) · [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 功能总览

- 一个入口拿所有本地数据：股票列表、K 线、交易日历、申万行业、指数、宏观
- 屏蔽底层数据库差异：你写"查日 K"，它自己去连 DuckDB / PostgreSQL / MySQL
- 内置股票池过滤：按地区、行业、板块、交易所、上市状态做包含 / 排除
- K 线默认返回前复权，同时附带原始价和后复权，策略不用自己算复权
- 给整个 NTQ 的策略、回测、标签、扫描共享同一份数据视图

## 配置说明

主要配置在 **数据库引擎** 上，路径是 `userspace/system/config/database/common.json`（或同名环境配置文件）：

| 配项 | 在哪配 | 默认值 | 说明 |
|------|--------|--------|------|
| `database_type` | `userspace/system/config/database/common.json` | `duckdb` | 底层引擎：`duckdb`（默认，本地文件）/ `postgresql` / `mysql` |
| `use_sample_stock_list` | `data.json` | `null` | 开发用样本股票池大小；设为整数则只保留 N 只分层抽样股票，节省磁盘和抓取时间 |
| 连接信息（host / port / user / password / database） | `userspace/system/config/database/<engine>.json` | 引擎相关 | 仅 PostgreSQL / MySQL 需要；DuckDB 不用 |

切引擎：把 `database_type` 改成目标引擎，并补一份对应引擎的连接 json。原数据不会自动迁移，需要重新跑一遍 `data_source` 抓取。

## 常见使用方式

### 场景 1：回测前查一只股票的日 K

1. 拿到 DataManager 实例。
2. 走 `stock.kline`，传入股票代码和周期（日 / 周 / 月）。
3. 拿到行级列表；顶层 `close` 已是前复权。

### 场景 2：查全市场股票列表（含已退市）

1. 走 `stock.list.load`。
2. 想要按维度筛（比如"剔除银行、只看沪深主板"），改用 `filter_ids`，传 include / exclude。
3. 想先看有哪些可选维度值，用 `load_filter_options`。

### 场景 3：查某段交易日

1. 走 `calendar`，给起止日期。
2. 返回的是真实交易日列表，已剔除周末和节假日。

### 场景 4：开发阶段想用小型股票池加速

1. 在 `data.json` 把 `use_sample_stock_list` 设成一个整数（比如 200）。
2. 之后所有抓取、写库、查询都只用这 200 只样本。
3. 想恢复全量，把它改回 `null` 或删掉这一行。

### 场景 5：换底层数据库引擎

1. 改 `database/common.json` 的 `database_type`。
2. 如果是 PostgreSQL / MySQL，补一份 `<engine>.json` 的连接信息。
3. 重启进程；首次需要重跑 `data_source` 把数据拉进新库。

## 常见坑与注意事项

- **改了 `database_type` 后查不到数据：** 引擎只决定"连哪个库"，不会自动迁移数据。换引擎后需要重新跑一遍抓取。
- **K 线价格和券商 App 不一致：** 顶层默认前复权。如果要原始价，取行内的 `raw` 字段。
- **样本池忘了关：** 在 `data.json` 设过 `use_sample_stock_list` 后，全市场扫描 / 全量回测会自动缩到样本池，结果会"看起来少了很多股票"。正式发布前记得清掉。
- **多个进程同时打开 DuckDB：** 本地 DuckDB 文件不擅长多进程并发写。回测 worker 走只读通道；写库集中由主进程做。
- **加了新表但 `list_tables` 看不到：** 表是启动时发现并注册的；新加表后需要重启进程，或检查表目录结构是否符合约定。

## 相关文档

- [概览 README](../README.md)
- [公开 API](../API.md)
- [架构](./ARCHITECTURE.md)
- [术语表](../glossary.yaml)
- [快速上手](../QUICKSTART.md)
