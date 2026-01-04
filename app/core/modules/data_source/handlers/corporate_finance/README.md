# Corporate Finance Handler 文档

**版本**: 2.0  
**最后更新**: 2025-12-23

## 概述

`CorporateFinanceHandler` 负责从 Tushare API 获取企业财务指标数据（季度数据），并存储到 `corporate_finance` 表中。

## 数据源信息

- **数据源名称**: `corporate_finance`
- **更新类型**: `incremental`（增量更新）
- **数据格式**: 季度数据（YYYYQ[1-4] 格式）
- **API 提供方**: Tushare (`fina_indicator` 接口)
- **API 限流**: 500 次/分钟

## 数据表结构

### 主键
- `(id, quarter)` 复合主键
  - `id`: varchar(16) - 股票代码（如 "000001.SZ"）
  - `quarter`: varchar(16) - 季度（如 "2024Q3"）

### 数据字段
包含以下财务指标类别：
- **盈利能力指标**: eps, dt_eps, roe, roe_dt, roa, netprofit_margin, gross_profit_margin, op_income, roic, ebit, ebitda, dtprofit_to_profit, profit_dedt
- **成长能力指标**: or_yoy, netprofit_yoy, basic_eps_yoy, dt_eps_yoy, tr_yoy
- **偿债能力指标**: netdebt, debt_to_eqt, debt_to_assets, interestdebt, assets_to_eqt, quick_ratio, current_ratio
- **运营能力指标**: ar_turn
- **资产状况指标**: bps
- **现金流指标**: ocfps, fcff, fcfe

所有数值字段类型为 `float`，且 `isRequired: true`（缺失值会被转换为 0.0）。

## 数据更新策略

### 核心设计原则

1. **滚动窗口机制**: 默认每次至少覆盖最近 3 个季度（`ROLLING_QUARTERS = 3`）
2. **批次轮转机制**: 当数据表不为空时，将股票列表按轮转游标切成批次，每次 run 只处理约 1/10 的股票（`RENEW_ROLLING_BATCH = 10`）
3. **数据一致性优先**: 对于长期未更新的股票，不做最大季度数限制，从上次更新的季度起点一路补到当前有效季度

### 更新流程

#### 1. 首次运行（数据库为空）

- **行为**: 对传入的 `stock_list` 中的所有股票进行**全量拉取**
- **起始日期**: `data_default_start_date`（默认 20080101）
- **结束日期**: `latest_completed_trading_date`
- **目的**: 建立基准数据

#### 2. 后续运行（数据库不为空）

##### 2.1 批次选择（轮转机制）

- 从 `meta_info` 表读取 `corporate_finance_batch_offset`（存储在 `id=1` 的记录中）
- 计算批次大小：`batch_size = max(1, len(stock_list) // RENEW_ROLLING_BATCH)`
- 根据 offset 做环形切片，选出本次要处理的股票子集
- 处理完成后，更新 offset 为 `(offset + batch_size) % len(stock_list)`，写回 `meta_info` 表

**示例**:
- `stock_list` 长度 = 5000
- `RENEW_ROLLING_BATCH = 10`
- 每次处理约 500 只股票
- 10 次运行后，整个股票池都会被轮转覆盖

##### 2.2 股票更新范围计算

对每只选中的股票，根据其在数据库中的 `last_updated_quarter`（通过 `MAX(quarter) GROUP BY id` 查询得到）决定更新范围：

**情况 A: 从未有财报数据（新股）**
- `start_date = data_default_start_date`
- `end_date = latest_completed_trading_date`
- 行为：全量拉取历史数据

**情况 B: 已有数据，且进度在最近 3 个季度内**
- 计算当前季度：`current_quarter = DateUtils.get_current_quarter(latest_completed_trading_date)`
- 计算滚动窗口最老季度：`window_oldest_quarter = current_quarter 往前推 (ROLLING_QUARTERS - 1) 个季度`
- 如果 `next_quarter(last_updated_quarter) <= window_oldest_quarter`：
  - `start_date = get_start_date_of_quarter(window_oldest_quarter)`
  - `end_date = latest_completed_trading_date`
  - **行为**: 只刷新最近 3 个季度（实现滚动覆盖）

**情况 C: 已有数据，但落后超过 3 个季度**
- `start_date = get_start_date_of_quarter(last_updated_quarter)`
- `end_date = latest_completed_trading_date`
- **行为**: 从上次更新的季度起点开始，一路补到当前有效季度（逐步追平）

#### 3. API 调用

- **方法**: `TushareProvider.get_finance_data(ts_code, start_date, end_date)`
- **底层 API**: Tushare `fina_indicator`
- **参数说明**:
  - `ts_code`: 股票代码（如 "000001.SZ"）
  - `start_date`: 起始日期（YYYYMMDD 格式）
  - `end_date`: 结束日期（YYYYMMDD 格式，直接使用 `latest_completed_trading_date`）

**重要**: Tushare API 会自动过滤到实际已披露的财报数据，即使传入今天或未来的日期，也只会返回已存在的财报记录，不会返回空数据或未来数据。

#### 4. 数据标准化

- 将 Tushare 返回的 DataFrame 转换为字典列表
- 使用 `DBService.clean_nan_in_list()` 清理所有 NaN 值
- 字段映射：
  - `ts_code` → `id`
  - `end_date` → `quarter`（通过 `DateUtils.date_to_quarter()` 转换）
  - 其他字段直接映射（注意：`grossprofit_margin` → `gross_profit_margin`）
- 所有数值字段通过 `safe_float()` 函数转换，NaN 值统一转换为 `0.0`

#### 5. 数据保存

- **保存时机**: 每个 Task 执行完成后立即保存（`after_single_task_execute` 钩子）
- **保存方式**: 使用 `CorporateFinanceModel.save_finance_data()`，内部调用 `replace()` 方法
- **去重机制**: 基于主键 `(id, quarter)` 自动去重/覆盖

## 配置参数

### Handler 类属性

- `ROLLING_QUARTERS = 3`: 滚动窗口季度数（默认每次刷新最近 3 个季度）
- `RENEW_ROLLING_BATCH = 10`: 批次轮转数（每次处理约 1/10 的股票）

### Context 参数

- `latest_completed_trading_date`: 最新完成交易日（YYYYMMDD 格式）
  - 如果未提供，会从 `DataManager.get_latest_completed_trading_date()` 获取
- `stock_list`: 股票列表（可选）
  - 如果未提供，handler 会从数据库查询所有需要更新的股票
- `dry_run`: 干运行模式（可选，默认 False）
  - 如果为 True，只执行逻辑不写入数据库

## 数据质量保证

### NaN 值处理

- 使用 `DBService.clean_nan_in_list()` 统一清理 DataFrame 转换后的 NaN 值
- 所有数值字段通过 `safe_float()` 函数转换，确保不会有 NaN 写入数据库
- 缺失值统一转换为 `0.0`（符合 schema 中 `isRequired: true` 的要求）

### 数据一致性

- 使用主键 `(id, quarter)` 的 `replace` 机制，确保同一季度的数据只会有一条记录
- 每次更新都会覆盖旧数据，保证数据的一致性

## 性能优化

1. **批次轮转**: 避免单次任务处理过多股票，减少 API 调用压力
2. **滚动窗口**: 只刷新最近 N 个季度，避免重复拉取历史数据
3. **单股票保存**: 每个股票的数据获取完成后立即保存，避免大批量写入导致的风险

## 依赖关系

- **数据源依赖**: 无（`dependencies = []`）
- **数据库依赖**: 
  - `corporate_finance` 表（存储财务数据）
  - `meta_info` 表（存储批次轮转游标，`id=1` 对应 `corporate_finance_batch_offset`）

## 使用示例

```python
from app.data_source.data_source_manager import DataSourceManager

# 初始化
ds_manager = DataSourceManager()
await ds_manager.initialize()

# 更新企业财务数据
context = {
    "latest_completed_trading_date": "20251223",
    "stock_list": [...]  # 可选，如果不提供则处理所有需要更新的股票
}

result = await ds_manager.renew_corporate_finance_data(
    latest_completed_trading_date="20251223",
    stock_list=stock_list,  # 可选
    dry_run=False
)
```

## 注意事项

1. **首次运行**: 如果数据库为空，会对所有股票进行全量拉取，可能需要较长时间
2. **批次轮转**: 长期来看，所有股票都会被公平轮转覆盖，不会出现某只股票"永远轮不到"的情况
3. **数据更新频率**: 建议每天或每周运行一次，确保数据及时更新
4. **API 限流**: Tushare `fina_indicator` 接口限流为 500 次/分钟，框架会自动处理限流

## 未来改进计划

1. **定期健康检查**: 每 2 周或 1 个月运行一次，查找数据库中财务数据为 0 的可疑记录，重新爬取
2. **Daily Job**: 将更新机制改为每日自动运行的定时任务

## 版本历史

- **v2.0** (2025-12-23): 
  - 重构数据更新策略，实现滚动窗口 + 批次轮转机制
  - 优化 NaN 值处理，使用通用的 `DBService.clean_nan_*` 方法
  - 改进批次轮转机制，使用 `meta_info` 表存储游标
  - 简化季度判断逻辑，直接使用 `latest_completed_trading_date` 作为 end_date
