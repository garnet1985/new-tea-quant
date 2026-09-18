---
title: NTQ 约定
aliases:
  - conventions
  - naming
  - paths
  - rules
  - 约定
  - 路径
  - 命名
summary: NTQ 的路径、命名、CLI 缩写与配置合并约定。
---

# NTQ 命名规范与约定

## 路径规范

### 用户路径

策略在 `userspace/strategies/`；扩展（标签、契约、数据源、表、适配器）在 `userspace/extensions/`：

| 类型     | 路径                                                 | 最小文件                           |
| ------ | -------------------------------------------------- | ------------------------------ |
| 策略     | `userspace/strategies/{name}/`                     | `strategy.py` + `settings.py`  |
| 标签场景   | `userspace/extensions/tags/{name}/`                | `tag.py` + `settings.py`       |
| 数据契约   | `userspace/extensions/data_contract/{name}/`       | `declaration.py` + `loader.py` |
| 数据源    | `userspace/extensions/data_source/`                | `mapping.py`（注册表）              |
| 数据表    | `userspace/extensions/tables/{name}/`              | `schema.py`（+ 可选 `model.py`）   |
| 扫描适配器  | `userspace/extensions/adapters/{name}/`            | `adapter.py`                   |
| AI 供应商 | `userspace/extensions/assistant/providers/{name}/` | `config.py`                    |

### 系统配置路径

| 配置            | 路径                                                                   |
| ------------- | -------------------------------------------------------------------- |
| 数据设置          | `userspace/system/config/data.json`                                  |
| 数据库类型         | `userspace/system/config/database/common.json`                       |
| DuckDB 配置     | `userspace/system/config/database/duckdb.json`                       |
| MySQL 配置      | `userspace/system/config/database/mysql.json`                        |
| PostgreSQL 配置 | `userspace/system/config/database/postgresql.json`                   |
| 性能参数          | `userspace/system/config/worker.json`（可选，覆盖默认）                       |
| DuckDB 数据库文件  | `userspace/system/db/data.duckdb` / `tag.duckdb` / `strategy.duckdb` |

### 内置路径

| 内容         | 路径                                         |
| ---------- | ------------------------------------------ |
| 内置表 schema | `core/tables/{category}/`                  |
| 默认配置       | `core/default_config/database/`            |
| 演示策略       | `userspace/strategies/demo/`               |
| 策略模板       | `userspace/strategies/_template/`          |
| 配置示例       | `userspace/strategies/settings_example.py` |

## 命名规范

### 策略

- 策略 key：`snake_case`，如 `rsi_v1`、`macd_golden_cross`

- 策略目录名：和 `meta.key` 一致。`python cli.py -n NAME` 只复制模板，**不会**把已有的 `meta.key` 改成 NAME（模板仍是 `empty_strategy`），创建后立刻改掉

- 类名：`PascalCase`，如 `RsiV1Strategy`

- CLI 引用：`--strategy rsi_v1` 或 `--strategy demo/rsi_v1`

### 标签

- 场景 key：`snake_case`，如 `volume_surge`、`industry_map`

- settings 里的 `meta.key` 是唯一标识

### 数据表

- 表名：`snake_case`，如 `stock_kline_daily`、`dragon_typer`

- schema 文件里的 `table_name` 字段必须和目录名一致

- storage\_domain：`data` / `tag` / `strategy`（对应三个 DuckDB 文件）

### DataKey

- 格式：`{domain}.{entity}.{frequency}`，如 `stock.kline.daily`、`market.index.daily`

- 在 `data_contract/contracts.py` 的 `DATA_KEY` 枚举中注册

## 配置合并规则

### 深度合并（大部分配置）

用户配置和默认配置逐层合并：

- 用户有的字段覆盖默认值

- 用户没有的字段用默认值

- 列表/字典递归合并

适用：`data.json`、`worker.json`、`database/*.json`

### 浅层覆盖（特殊字段）

用户值完全替换默认值，不追加：

- `benchmark_stock_index_list`：用户写了就完全替换默认指数列表

### 策略 settings.py

- 不和 `data.json` 等全局配置合并

- 加载时会对缺块补默认，省略某些块也能跑；新建仍应用模板写全（`data` / `goal` / `simulation` / `portfolio` / `fees`），不要只留 `meta.key`

- 不要写 `data.base.params.adjust`：该字段会被剥掉。钩子里顶层 `open/close` 已是前复权

## CLI 命令规范

### 入口

- 用户命令：`python cli.py`

- 开发命令：`python devcli.py`

- 旧命令 `python start-cli.py` 已废弃

### 命令格式

```
python cli.py xx [-f] [--strategy NAME] [--param value]
```

- `xx`：命令缩写（如 `sp` = strategy\_price\_factor）

- `-f`：全局强制刷新/重算

- `-n PATH`：全局从模板新建

- `--verbose`：详细日志

### 命令缩写对照

| 缩写    | 全称                         | 用途       |
| ----- | -------------------------- | -------- |
| `s`   | strategy\_simulate         | 价格因子→组合（缺枚举才补跑） |
| `se`  | strategy\_enumerate        | 第一步：枚举   |
| `sp`  | strategy\_price\_factor    | 第二步：价格因子 |
| `so`  | strategy\_portfolio        | 第三步：组合模拟 |
| `sd`  | strategy\_decision         | 第四步：决策者  |
| `sdl` | strategy\_decision\_list   | 列出决策者会话  |
| `sdd` | strategy\_decision\_delete | 删除决策者会话  |
| `sa`  | strategy\_analyze          | 归因分析     |
| `c`   | scan                       | 扫描机会     |
| `r`   | renew                      | 更新数据     |
| `t`   | tag                        | 执行标签     |
| `ex`  | export\_strategy           | 导出策略包    |
| `im`  | import\_strategy           | 导入策略包    |
| `id`  | import\_data               | 导入数据包    |
| `u`   | update                     | 升级 core  |
| `v`   | version                    | 查看 NTQ 核心版本 |
| `spn` | strategy\_pin\_version     | 固定版本     |
| `sup` | strategy\_unpin\_version   | 取消固定     |
| `sdv` | strategy\_delete\_version  | 删除版本     |

### 易混命令

- 跑回测用 `s` / `se` / `sp` / `so`。`spn` **不是**运行回测，只固定一个已经存在的 version

- `v` 只打印 NTQ 核心版本，不是策略回测 version 列表

- 报告在 `{strategy}/results/simulations/{vid}/`（`enum/` `price/` `portfolio/`），**没有** `reports/` 目录

## 版本规范

- NTQ 版本在 `core/system.json` 的 `version` 字段

- 当前 0.5.x，API 不保证稳定

- 1.0 之后 API 基本稳定

- 升级方式：下载新代码，保留 `userspace/`，其他文件替换

## 策略钩子命名

- 方法名：`snake_case`，如 `has_opportunity`、`on_before_scan`

- `is_` 前缀：布尔判断，如 `is_stop_loss`、`is_take_profit`

- `on_` 前缀：事件回调，如 `on_before_scan`、`on_after_scan`、`on_calendar_asof`、`on_pick_portfolio_member`

## 配置字段命名

- `snake_case`：所有字段名

- `is_enabled`：布尔开关

- `max_xxx`：上限

- `min_xxx`：下限

- `xxx_rate`：比率

- `xxx_size`：大小/数量

- `xxx_mode`：模式枚举

## 错误处理约定

- 数据缺失时返回 `None` 或空列表，不抛异常

- 策略钩子里取数：`data = ctx.data.items_with_meta()`，`klines = data.get(ctx.base_data_key) or []`。`ctx.data` 不是函数

- 指标在 `settings.data.base.indicators` 声明，钩子读 K 线字段。不要手写 EMA，不能对 dict 列表做减法

- CLI 命令失败时返回非零退出码

- 回测中单个 job 失败时跳过并记录到 `failed_jobs`

## 数据库约定

- DuckDB 是默认数据库，零配置

- MySQL / PostgreSQL 需要额外安装和配置

- 三种数据库的表结构一致，schema.py 通用

- 环境变量可覆盖配置文件：`DB_HOST`、`DB_PORT`、`DB_USER`、`DB_PASSWORD`

- API key 类配置走环境变量，不存配置文件

