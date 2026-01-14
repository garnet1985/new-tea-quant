# Adj Factor Event Handler 文档

**版本**: 2.0  
**最后更新**: 2025-12-23

## 概述

`AdjFactorEventHandler` 负责计算和存储股票的复权因子事件数据。复权因子事件记录了股票除权除息日期的复权因子变化，用于后续的 K 线数据复权计算。

## 数据源信息

- **数据源名称**: `adj_factor_event`
- **更新类型**: `refresh`（全量替换更新）
- **数据格式**: 事件数据（按除权日期记录）
- **API 提供方**: 
  - Tushare (`adj_factor` 接口)
  - Tushare (`daily` 接口，用于获取原始收盘价)
  - EastMoney (`get_qfq_kline` 接口，用于获取前复权价格)
- **API 限流**: 
  - Tushare `adj_factor`: 800 次/分钟
  - Tushare `daily`: 700 次/分钟
  - **EastMoney: 60 次/分钟** ⚠️ **这是系统的主要瓶颈**

## 数据表结构

### 主键
- `(id, event_date)` 复合主键
  - `id`: varchar(16) - 股票代码（如 "000001.SZ"）
  - `event_date`: varchar(16) - 除权日期（YYYYMMDD 格式）

### 数据字段
- `factor`: float - 复权因子（相对于前一个事件日的累积复权因子）
- `qfq_diff`: float - 前复权价格与原始收盘价的差值（qfq_price - raw_price）
- `last_update`: datetime - 记录最后更新时间（用于判断是否需要重新计算）

## 核心算法

### 复权因子计算原理

复权因子事件的计算基于以下数据源：

1. **Tushare `adj_factor`**: 提供每个交易日的复权因子（相对于上市首日）
2. **Tushare `daily_kline`**: 提供原始收盘价（未复权）
3. **EastMoney `get_qfq_kline`**: 提供前复权价格（已复权）

**计算逻辑**:
- 找出所有 `adj_factor` 发生变化的日期（除权除息日）
- 对于每个事件日：
  - 获取该日的原始收盘价（`raw_price`，来自 Tushare daily_kline）
  - 获取该日的前复权价格（`qfq_price`，来自 EastMoney）
  - 计算 `qfq_diff = qfq_price - raw_price`
  - 计算相对于前一个事件日的复权因子（`factor`）

**特殊处理**:
- **第一根 K 线日期**: 即使没有 `adj_factor` 变化，也会为第一根 K 线日期创建一个事件，因子从 EastMoney 的第一个 K 线数据推导
- **非交易日处理**: 如果事件日期是非交易日，会查找最近的前一个交易日的数据
- **数据缺失处理**: 如果某个事件日无法获取原始收盘价或前复权价格，该事件会被跳过（记录警告日志）

## 数据更新策略

### 核心设计原则

**⚠️ 关键设计目标：最小化 EastMoney API 调用次数**

EastMoney API 的限流为 **60 次/分钟**，这是整个系统的**主要瓶颈**。因此，本 Handler 的所有设计都围绕减少 EastMoney API 调用次数展开：

1. **全量 API 调用策略**: 对每只股票只调用一次 EastMoney API，获取全量前复权价格数据，而不是按事件数多次调用。这大幅减少了 API 调用次数：
   - **优化前**: 如果一只股票有 10 个复权事件，需要调用 10 次 EastMoney API
   - **优化后**: 每只股票只调用 1 次 EastMoney API，获取所有日期的前复权价格，然后在内存中查找需要的事件日价格
   - **效果**: 对于 4000+ 只股票，如果平均每只股票有 10 个事件，优化前需要 40000+ 次调用（需要 666+ 分钟），优化后只需要 4000+ 次调用（需要 67+ 分钟）

2. **全量替换机制**: 每次更新某只股票时，先删除该股票的所有旧记录，然后重新计算并保存。这确保了数据一致性，同时避免了复杂的增量更新逻辑。

3. **批量筛选机制**: 通过 SQL 查询找出超过 `update_threshold_days` 天未更新的股票，避免重复计算。这减少了需要更新的股票数量，从而减少了 EastMoney API 调用次数。

4. **CSV 缓存机制**: 支持从 CSV 文件快速恢复数据（表为空时），以及定期导出季度 CSV 备份。这避免了在数据恢复时的大量 API 调用。

### 更新流程

#### 步骤 0: CSV 导入（如果表为空）

- **检查条件**: 表为空且存在有效的 CSV 文件
- **行为**: 从当前季度的 CSV 文件导入数据
- **CSV 文件位置**: `app/data_source/defaults/handlers/adj_factor_event/adj_factor_events_YYYYQ[1-4].csv`
- **CSV 格式**: 包含 `id`, `event_date`, `factor`, `qfq_diff` 字段

#### 步骤 1: 批量查询需要更新的股票

- **查询逻辑**: 
  - 从数据库查询每只股票的 `MAX(last_update)`（按 `id` 分组）
  - 筛选出以下两类股票：
    1. **新股票**: 在 `stock_list` 中但数据库中没有记录的股票
    2. **过期股票**: `last_update` 距离 `latest_completed_trading_date` 超过 `update_threshold_days` 天的股票

- **配置参数**: `update_threshold_days`（默认 15 天）

#### 步骤 2: 生成 Tasks（全量 API 调用）

对每只需要更新的股票，生成一个 `DataSourceTask`，包含 3 个全量 API 调用：

1. **Tushare `adj_factor` API**:
   - 参数: `ts_code`, `start_date` (默认起始日期), `end_date` (最新完成交易日)
   - 返回: 全量复权因子数据（每个交易日的因子值）

2. **Tushare `daily_kline` API**:
   - 参数: `ts_code`, `start_date`, `end_date`
   - 返回: 全量日线数据（包含原始收盘价）

3. **EastMoney `get_qfq_kline` API**:
   - 参数: `secid` (转换后的 EastMoney 股票代码), `start_date`, `end_date`
   - 返回: 全量前复权 K 线数据（字符串格式，需要解析）

**优化说明（关键）**: 
- **EastMoney API 调用优化**: 使用全量 API 调用，将 EastMoney API 调用次数从"事件数"降低到"股票数"
  - **优化前**: 如果一只股票有 10 个复权事件，需要调用 10 次 EastMoney API（每个事件日调用一次）
  - **优化后**: 每只股票只调用 1 次 EastMoney API，获取全量前复权价格数据，然后在内存中查找需要的事件日价格
  - **实际效果**: 对于 4000+ 只股票，如果平均每只股票有 10 个事件，优化前需要 40000+ 次 EastMoney API 调用（需要 666+ 分钟），优化后只需要 4000+ 次调用（需要 67+ 分钟），**减少了 90% 的 API 调用时间**
- **Tushare API 调用**: 同样使用全量 API 调用，将调用次数从"事件数 × 2"降低到"股票数 × 2"（adj_factor + daily_kline）
- **数据获取策略**: 每个股票的所有数据一次性获取，便于后续计算，同时最大化利用每次 API 调用的数据量

#### 步骤 3: 数据计算与保存（`after_single_task_execute`）

对每个 Task 执行完成后，立即进行以下处理：

1. **删除旧数据**: 删除该股票的所有旧复权事件记录（实现全量替换）
2. **解析 API 结果**:
   - 解析 `adj_factor_df`，找出所有因子变化的日期
   - 解析 `daily_kline_df`，构建 `日期 -> 原始收盘价` 的映射
   - 解析 `eastmoney_result`，构建 `日期 -> 前复权价格` 的映射
3. **计算复权事件**:
   - 调用 `helper.build_adj_factor_events()` 计算所有事件
   - 处理第一根 K 线日期的特殊逻辑
   - 处理非交易日的数据查找（查找最近的前一个交易日）
4. **立即保存**: 使用 `AdjFactorEventModel.save_events()` 保存该股票的所有事件

**保存时机**: 每个股票的数据计算完成后立即保存，实现增量保存，避免大批量写入导致的风险

#### 步骤 4: CSV 导出（`after_normalize`）

- **触发条件**: 当前季度还没有 CSV 文件
- **导出内容**: 导出当前季度所有股票的复权事件数据
- **文件命名**: `adj_factor_events_YYYYQ[1-4].csv`
- **用途**: 
  - 数据备份
  - 快速恢复（表为空时可以从 CSV 导入）

## 配置参数

### Handler 类属性

- `update_threshold_days = 15`: 更新阈值天数（默认 15 天）
  - 如果股票的 `last_update` 距离当前日期超过此阈值，会重新计算
- `max_workers = 10`: 最大线程数（用于多线程处理，当前版本主要用于 Task 执行）

### Context 参数

- `latest_completed_trading_date`: 最新完成交易日（YYYYMMDD 格式）
  - 如果未提供，会从 `DataManager.service.calendar.get_latest_completed_trading_date()` 获取
- `stock_list`: 股票列表（可选）
  - 如果未提供，handler 会从数据库查询所有需要更新的股票
- `dry_run`: 干运行模式（可选，默认 False）
  - 如果为 True，只执行逻辑不写入数据库

## 数据质量保证

### 数据验证

- **必需数据检查**: 
  - `adj_factor` 数据为空时，跳过该股票
  - `daily_kline` 数据为空时，跳过该股票
  - 如果没有第一根 K 线数据（EastMoney 和 daily_kline 都没有），跳过该股票

- **非交易日处理**: 
  - 如果事件日期是非交易日，会查找最近的前一个交易日的原始收盘价和前复权价格
  - 使用 `helper.get_raw_price_for_date()` 和 `helper.get_eastmoney_qfq_for_date()` 方法

- **数据缺失处理**: 
  - 如果某个事件日无法获取原始收盘价，记录警告并跳过该事件
  - 如果某个事件日无法获取前复权价格，`qfq_diff` 设为 0.0，记录警告

### 数据一致性

- **全量替换机制**: 每次更新某只股票时，先删除所有旧记录，然后保存新计算的结果
- **主键去重**: 使用主键 `(id, event_date)` 确保同一股票同一事件日只有一条记录

## 性能优化

### EastMoney API 限流优化（核心优化）

**问题**: EastMoney API 限流为 60 次/分钟，这是系统的主要瓶颈。

**解决方案**:
1. **全量 API 调用策略**: 每个股票只调用 1 次 EastMoney API，获取全量前复权价格数据
   - 将 API 调用次数从"事件数"降低到"股票数"
   - 对于 4000+ 只股票，如果平均每只股票有 10 个事件，优化前需要 40000+ 次调用（666+ 分钟），优化后只需要 4000+ 次调用（67+ 分钟）
   - **减少了 90% 的 API 调用时间**

2. **批量筛选机制**: 一次 SQL 查询找出所有需要更新的股票，避免重复计算
   - 减少需要更新的股票数量，从而减少 EastMoney API 调用次数

3. **CSV 缓存机制**: 支持从 CSV 快速恢复数据，避免在数据恢复时的大量 API 调用

### 其他优化

1. **Tushare API 调用优化**: 同样使用全量 API 调用，将调用次数从"事件数 × 2"降低到"股票数 × 2"
2. **增量保存**: 每个股票的数据计算完成后立即保存，避免大批量写入导致的风险
3. **数据获取策略**: 每个股票的所有数据一次性获取，最大化利用每次 API 调用的数据量

## 依赖关系

- **数据源依赖**: 无（`dependencies = []`）
- **数据库依赖**: 
  - `adj_factor_event` 表（存储复权事件数据）
  - `stock_list` 表（可选，用于获取股票列表）

## 使用示例

```python
from app.core.modules.data_source.data_source_manager import DataSourceManager

# 初始化
ds_manager = DataSourceManager()
await ds_manager.initialize()

# 更新复权因子事件数据
context = {
    "latest_completed_trading_date": "20251223",
    "stock_list": [...]  # 可选
}

result = await ds_manager.renew_adj_factor_data(
    latest_completed_trading_date="20251223",
    stock_list=stock_list,  # 可选
    dry_run=False
)
```

## 注意事项

1. **EastMoney API 限流**: EastMoney API 限流为 60 次/分钟，这是系统的主要瓶颈。所有设计都围绕减少 EastMoney API 调用次数展开。如果需要更新大量股票，建议：
   - 使用批量筛选机制，只更新超过阈值的股票
   - 利用 CSV 缓存机制，避免重复计算
   - 考虑分批次更新，避免一次性更新所有股票

2. **全量替换**: 每次更新某只股票时，会删除该股票的所有旧记录，然后重新计算。这是设计上的选择，确保数据的一致性，同时简化了逻辑。

3. **第一根 K 线**: 即使没有复权因子变化，也会为第一根 K 线日期创建一个事件，因子从 EastMoney 的第一个 K 线数据推导。

4. **数据依赖**: 复权因子事件的计算依赖于 Tushare 的 `adj_factor` 和 `daily_kline` 数据，以及 EastMoney 的前复权价格数据。如果这些数据源有问题，可能会影响计算结果。

5. **CSV 备份**: 建议定期检查 CSV 文件是否存在且未过期，确保可以快速恢复数据，避免在数据恢复时的大量 API 调用。

## 版本历史

- **v2.0** (2025-12-23): 
  - 重构为全量 API 调用模式（每个股票 3 个全量 API 调用）
  - 优化数据保存机制（每个股票完成后立即保存）
  - 改进非交易日处理逻辑（查找最近的前一个交易日）
  - 优化第一根 K 线日期的因子计算逻辑（优先使用 EastMoney 数据）
  - 改进 CSV 导入/导出机制
