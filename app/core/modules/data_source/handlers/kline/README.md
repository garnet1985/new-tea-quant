# Kline Handler 文档

**版本**: 2.0  
**最后更新**: 2025-12-23

## 概述

`KlineHandler` 负责从 Tushare API 获取股票的 K 线数据（日线/周线/月线）和基本面指标数据，合并后存储到 `stock_kline` 表中。

## 数据源信息

- **数据源名称**: `kline`
- **更新类型**: `incremental`（增量更新）
- **数据格式**: 时序数据（按日期记录）
- **支持周期**: daily（日线）、weekly（周线）、monthly（月线）
- **API 提供方**: Tushare
  - `daily` / `weekly` / `monthly` 接口（K 线价格和成交量数据）
  - `daily_basic` 接口（基本面指标）
- **API 限流**: 
  - `daily` / `weekly` / `monthly`: 700 次/分钟
  - `daily_basic`: 700 次/分钟

## 数据表结构

### 主键
- `(id, date, term)` 复合主键
  - `id`: varchar(16) - 股票代码（如 "000001.SZ"）
  - `date`: varchar(16) - 日期（YYYYMMDD 格式）
  - `term`: varchar(16) - 周期（"daily" / "weekly" / "monthly"）

### 数据字段

#### K 线价格和成交量数据（来自 daily/weekly/monthly API）
- `open`: float - 开盘价
- `highest`: float - 最高价
- `lowest`: float - 最低价
- `close`: float - 收盘价
- `pre_close`: float - 前收盘价
- `price_change_delta`: float - 涨跌额
- `price_change_rate_delta`: float - 涨跌幅（%）
- `volume`: int - 成交量（手）
- `amount`: float - 成交额（千元）

#### 基本面指标数据（来自 daily_basic API）
- `turnover_rate`: float - 换手率（%）
- `free_turnover_rate`: float - 自由流通换手率（%）
- `volume_ratio`: float - 量比
- `pe`: float - 市盈率（总市值/净利润）
- `pe_ttm`: float - 市盈率 TTM
- `pb`: float - 市净率（总市值/净资产）
- `ps`: float - 市销率
- `ps_ttm`: float - 市销率 TTM
- `dv_ratio`: float - 股息率
- `dv_ttm`: float - 股息率 TTM
- `total_share`: int - 总股本（万股）
- `float_share`: int - 流通股本（万股）
- `free_share`: int - 自由流通股本（万股）
- `total_market_value`: float - 总市值（万元）
- `circ_market_value`: float - 流通市值（万元）

## 核心设计

### 任务组织方式

**以股票为单位**: 每个股票创建一个 `DataSourceTask`，包含 3-4 个 `ApiJob`：

1. **`get_daily_kline`** - 日线价格和成交量数据（如果 daily 周期需要更新）
2. **`get_weekly_kline`** - 周线价格和成交量数据（如果 weekly 周期需要更新）
3. **`get_monthly_kline`** - 月线价格和成交量数据（如果 monthly 周期需要更新）
4. **`get_daily_basic`** - 基本面指标数据（**只调用一次**，所有周期共享）

**优势**:
- `daily_basic` 只调用一次，减少 API 调用次数（从 6N 降到 4N，N 为股票数）
- 逻辑更清晰（一个股票的所有数据一起处理）
- 不需要跨线程缓存机制

### 数据合并策略

- **LEFT JOIN**: K 线数据与 `daily_basic` 数据按 `(id, date)` 合并
- **前向填充**: 对于基本面指标字段，在 `daily_basic` 数据范围内使用前向填充（ffill）
- **范围限制**: 只在 `daily_basic` 有数据的日期范围内填充，不跨数据范围填充
  - 例如：如果 K 线数据从 2008 年开始，但 PE、PB 从 2020 年才开始有，那么 2008-2019 年的 PE、PB 保持为 0（因为 schema 要求 NOT NULL）
- **默认值处理**: 对于填充后仍然为 NaN 的字段，使用默认值 0（因为 schema 要求 `isRequired: true`）

## 数据更新策略

### 更新范围计算

#### 1. 结束日期计算（`before_fetch`）

- **daily**: 使用 `latest_completed_trading_date`（最新完成交易日）
- **weekly**: 使用 `DateUtils.get_previous_week_end(latest_completed_trading_date)`（上个完整周的周日）
- **monthly**: 使用 `DateUtils.get_previous_month_end(latest_completed_trading_date)`（上个完整月的最后一天）

#### 2. 起始日期计算（`fetch`）

对每个股票，查询数据库获取该股票在 3 个周期的最新日期：

- **已有数据**: 从 `最新日期 + 1 天` 开始
- **新股票**: 从 `data_default_start_date`（默认 20080101）开始

#### 3. 更新条件判断

- **daily**: 如果 `start_date <= end_date`，需要更新
- **weekly**: 只有当时间间隔 >= 1 周时才更新
- **monthly**: 只有当时间间隔 >= 1 个月时才更新

**注意**: 如果某个周期的数据已经是最新的（`start_date > end_date`），该周期会被跳过，不会生成对应的 ApiJob。

### 数据保存策略

#### 增量保存（`after_single_task_execute`）

- **保存时机**: 每个 Task 执行完成后立即保存
- **保存内容**: 该股票的所有周期（daily/weekly/monthly）的合并数据
- **去重机制**: 使用 `_saved_tasks` 集合记录已保存的任务，避免重复保存

#### 兜底保存（`after_all_tasks_execute`）

- **保存时机**: 所有 Tasks 执行完成后
- **保存内容**: 只保存尚未通过增量保存机制保存的任务（避免重复保存）
- **用途**: 处理增量保存可能因为中断而未完成的情况

## 配置参数

### Handler 类属性

- `TERM_MAPPING`: 周期映射表
  - `daily` → `get_daily_kline`
  - `weekly` → `get_weekly_kline`
  - `monthly` → `get_monthly_kline`

### Context 参数

- `stock_list`: 股票列表（可选）
  - 如果未提供，handler 会从数据库查询（使用过滤规则，排除 ST、科创板等）
- `latest_completed_trading_date`: 最新完成交易日（YYYYMMDD 格式）
  - 如果未提供，会从 `DataManager.get_latest_completed_trading_date()` 获取
- `dry_run`: 干运行模式（可选，默认 False）
  - 如果为 True，只执行逻辑不写入数据库

## 数据质量保证

### NaN 值处理

- 使用 `DBService.clean_nan_in_list()` 统一清理 DataFrame 转换后的 NaN 值
- 在 `_merge_kline_and_basic()` 方法中，对所有列使用 `pd.notna()` 检查，将 NaN 转换为 None
- 对于基本面指标字段，如果填充后仍然为 NaN，使用默认值 0（因为 schema 要求 `isRequired: true`）

### 数据验证

- **必需数据检查**: 
  - 如果 `daily_basic` 数据为空，该股票的所有周期数据都不会保存（记录警告，等待下次重试）
  - 如果某个周期的 K 线数据为空，该周期会被跳过

- **字段映射验证**: 
  - 确保所有必需字段都存在
  - 进行类型转换（数值字段转为 float，成交量转为 int）

### 数据一致性

- **主键去重**: 使用主键 `(id, date, term)` 确保同一股票同一日期同一周期只有一条记录
- **合并策略**: 使用 LEFT JOIN 确保所有 K 线数据都被保留，即使没有对应的 `daily_basic` 数据

## 性能优化

1. **批量查询**: 使用 `load_latest_records()` 方法一次性查询所有股票的所有周期的最新日期，避免 O(N×3) 查询
2. **共享 daily_basic**: `daily_basic` 只调用一次，所有周期共享，减少 API 调用次数
3. **增量保存**: 每个股票的数据获取完成后立即保存，避免大批量写入导致的风险
4. **智能跳过**: 只更新需要更新的周期，避免不必要的 API 调用

## 依赖关系

- **数据源依赖**: `["stock_list"]`（需要先更新股票列表）
- **数据库依赖**: 
  - `stock_kline` 表（存储 K 线数据）
  - `stock_list` 表（用于获取股票列表）

## 使用示例

```python
from app.core.modules.data_source.data_source_manager import DataSourceManager

# 初始化
ds_manager = DataSourceManager()
await ds_manager.initialize()

# 更新 K 线数据
context = {
    "latest_completed_trading_date": "20251223",
    "stock_list": [...]  # 可选，如果不提供则从数据库查询（已过滤）
}

result = await ds_manager.renew_kline_data(
    latest_completed_trading_date="20251223",
    stock_list=stock_list,  # 可选
    dry_run=False
)
```

## 注意事项

1. **daily_basic 依赖**: 如果 `daily_basic` API 调用失败或返回空数据，该股票的所有周期数据都不会保存。这是设计上的选择，确保数据的完整性。
2. **周期更新条件**: weekly 和 monthly 周期只有当时间间隔 >= 1 个完整周期时才会更新，避免频繁更新。
3. **数据填充范围**: 基本面指标的前向填充只在 `daily_basic` 有数据的日期范围内进行，不会跨数据范围填充，确保数据的准确性。
4. **默认值处理**: 对于 schema 要求 `isRequired: true` 的字段，如果无法获取数据，会使用默认值 0，而不是 NULL。

## 版本历史

- **v2.0** (2025-12-23): 
  - 重构为以股票为单位的任务组织方式（每个股票一个 Task，包含 3-4 个 ApiJob）
  - 优化 `daily_basic` 调用策略（只调用一次，所有周期共享）
  - 改进数据合并逻辑（LEFT JOIN + 范围限制的前向填充）
  - 优化增量保存机制（每个股票完成后立即保存）
  - 改进 NaN 值处理（使用通用的 `DBService.clean_nan_*` 方法）
  - 优化周期更新条件判断（weekly/monthly 需要间隔 >= 1 个完整周期）
