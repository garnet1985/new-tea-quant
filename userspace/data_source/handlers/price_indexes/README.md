# Price Indexes Handler 文档

**版本**: 2.0  
**最后更新**: 2025-12-23

## 概述

`PriceIndexesHandler` 负责从 Tushare API 获取宏观经济价格指数数据（CPI、PPI、PMI、货币供应量），按月份合并后存储到 `price_indexes` 表中。

## 数据源信息

- **数据源名称**: `price_indexes`
- **更新类型**: `incremental`（增量更新）
- **数据格式**: 月度数据（YYYYMM 格式）
- **API 提供方**: Tushare
  - `get_cpi` 接口（消费者价格指数）
  - `get_ppi` 接口（生产者价格指数）
  - `get_pmi` 接口（采购经理人指数）
  - `get_money_supply` 接口（货币供应量）
- **API 限流**: 
  - Tushare `get_cpi`: 500 次/分钟
  - Tushare `get_ppi`: 500 次/分钟
  - Tushare `get_pmi`: 500 次/分钟
  - Tushare `get_money_supply`: 500 次/分钟

## 数据表结构

### 主键
- `date` 主键
  - `date`: varchar(6) - 月份（YYYYMM 格式，如 "202412"）

### 数据字段

#### CPI 指标（消费者价格指数）
- `cpi`: float - CPI 当月值
- `cpi_yoy`: float - CPI 同比（year to year）
- `cpi_mom`: float - CPI 环比（month to month）

#### PPI 指标（生产者价格指数）
- `ppi`: float - PPI 当月值
- `ppi_yoy`: float - PPI 同比
- `ppi_mom`: float - PPI 环比

#### PMI 指标（采购经理人指数）
- `pmi`: float - PMI 综合指数
- `pmi_l_scale`: float - 大型企业 PMI
- `pmi_m_scale`: float - 中型企业 PMI
- `pmi_s_scale`: float - 小型企业 PMI

#### 货币供应量指标
- `m0`: float - M0 货币供应量
- `m0_yoy`: float - M0 同比
- `m0_mom`: float - M0 环比
- `m1`: float - M1 货币供应量
- `m1_yoy`: float - M1 同比
- `m1_mom`: float - M1 环比
- `m2`: float - M2 货币供应量
- `m2_yoy`: float - M2 同比
- `m2_mom`: float - M2 环比

所有数值字段类型为 `float`，且 `isRequired: true`（缺失值会被转换为 0.0）。

## 数据更新策略

### 核心设计原则

1. **滚动刷新机制**: 每次运行都刷新最近 N 个月的数据（默认 12 个月），确保数据一致性
   - 宏观经济数据可能会被修正，滚动刷新可以确保最近 N 个月的数据是最新的
   - 数据量小（每月只有一条记录），滚动刷新成本很低

2. **历史追赶机制**: 如果数据库最新日期距离当前超过 N 个月，从上次更新日期开始追赶

3. **首次运行处理**: 如果数据库为空，使用默认日期范围（最近 3 年）

### 更新流程

#### 1. 首次运行（数据库为空）

- **行为**: 使用默认日期范围（最近 3 年）
- **起始日期**: 当前年份 - 3 年的 1 月
- **结束日期**: 当前月份

#### 2. 后续运行（数据库不为空）

Handler 会根据数据库最新日期和当前月份的时间间隔，决定更新策略：

**情况 A：间隔 <= ROLLING_MONTHS（默认 12 个月）**
- **行为**: 滚动刷新最近 `ROLLING_MONTHS` 个月的数据
- **起始日期**: 当前月份往前推 `ROLLING_MONTHS` 个月
- **结束日期**: 当前月份
- **说明**: 即使数据已经是最新的，也会刷新最近 N 个月，确保数据一致性

**情况 B：间隔 > ROLLING_MONTHS**
- **行为**: 从数据库最新日期开始追赶（历史追赶）
- **起始日期**: 数据库最新日期的下一个月
- **结束日期**: 当前月份
- **说明**: 如果数据库落后超过 N 个月，会从上次更新日期开始追赶

#### 3. API 调用

对计算出的日期范围，生成一个 `DataSourceTask`，包含 4 个 `ApiJob`：

1. **Tushare `get_cpi` API**: 获取 CPI 数据
2. **Tushare `get_ppi` API**: 获取 PPI 数据
3. **Tushare `get_pmi` API**: 获取 PMI 数据
4. **Tushare `get_money_supply` API**: 获取货币供应量数据

**优化说明**: 
- 所有 API 调用都在同一个 Task 中，并行执行
- 每次请求返回的数据量很小（每月只有一条记录），API 调用成本低

#### 4. 数据合并（`normalize`）

从 4 个 API 的结果中合并数据：

1. **处理 CPI 数据**: 提取 `month`, `nt_val` (CPI 当月值), `nt_yoy` (CPI 同比), `nt_mom` (CPI 环比)
2. **处理 PPI 数据**: 提取 `month`, `ppi_accu` (PPI 当月值), `ppi_yoy` (PPI 同比), `ppi_mom` (PPI 环比)
3. **处理 PMI 数据**: 提取 `MONTH`, `PMI010000` (PMI 综合指数), `PMI010100` (大型企业), `PMI010200` (中型企业), `PMI010300` (小型企业)
4. **处理货币供应量数据**: 提取 `month`, `m0`, `m0_yoy`, `m0_mom`, `m1`, `m1_yoy`, `m1_mom`, `m2`, `m2_yoy`, `m2_mom`
5. **按月份合并**: 将所有数据按月份（YYYYMM 格式）合并到同一行
6. **默认值处理**: 对于缺失的字段，使用默认值 0.0（因为 schema 要求 `isRequired: true`）

**月份格式标准化**: 
- 支持多种月份格式（YYYYMM、YYYY-MM、YYYYMMDD 等）
- 统一转换为 YYYYMM 格式

#### 5. 数据保存（`after_normalize`）

- **清理 NaN 值**: 使用 `DBService.clean_nan_in_list` 清理所有 NaN 值，转换为 0.0
- **保存数据**: 使用 `PriceIndexesModel.save_price_indexes` 保存数据
- **去重机制**: 使用主键 `date` 确保同一月份只有一条记录（`replace` 操作）

## 配置参数

### Handler 类属性

- `ROLLING_MONTHS = 12`: 滚动刷新月份数（默认 12 个月）
  - 每次运行都刷新最近 N 个月的数据，确保数据一致性
- `default_date_range = {"years": 3}`: 默认日期范围（用于首次运行或数据库为空时）
  - 默认最近 3 年

### Context 参数

- `start_date`: 起始月份（YYYYMM 格式，可选）
  - 如果未提供，Handler 会自动计算
- `end_date`: 结束月份（YYYYMM 格式，可选）
  - 如果未提供，Handler 会自动计算

## 数据质量保证

### NaN 值处理

- 在 `normalize` 方法中，使用 `setdefault` 确保所有必需字段都有默认值 0.0
- 在 `after_normalize` 方法中，使用 `DBService.clean_nan_in_list` 统一清理所有 NaN 值，转换为 0.0

### 数据验证

- **月份格式验证**: 支持多种月份格式，统一转换为 YYYYMM 格式
- **字段映射验证**: 确保所有必需字段都存在，进行类型转换（数值字段转为 float）

### 数据一致性

- **主键去重**: 使用主键 `date` 确保同一月份只有一条记录
- **滚动刷新**: 每次运行都刷新最近 N 个月的数据，确保数据一致性（即使数据已经是最新的）

## 性能优化

1. **滚动刷新策略**: 每次运行都刷新最近 N 个月的数据，确保数据一致性
   - 数据量小（每月只有一条记录），滚动刷新成本很低
   - 避免了复杂的批次轮转机制（因为数据量小）

2. **并行 API 调用**: 所有 API 调用都在同一个 Task 中，并行执行

3. **历史追赶机制**: 如果数据库落后超过 N 个月，会从上次更新日期开始追赶

## 依赖关系

- **数据源依赖**: 无（`dependencies = []`）
- **数据库依赖**: 
  - `price_indexes` 表（存储价格指数数据）

## 使用示例

```python
from core.modules.data_source.data_source_manager import DataSourceManager

# 初始化
ds_manager = DataSourceManager()
await ds_manager.initialize()

# 更新价格指数数据
result = await ds_manager.renew_price_indexes_data()
```

## 注意事项

1. **滚动刷新**: 每次运行都会刷新最近 12 个月的数据，即使数据已经是最新的。这是设计上的选择，确保数据一致性（宏观经济数据可能会被修正）。

2. **数据量小**: 每月只有一条记录，滚动刷新成本很低，不需要复杂的批次轮转机制。

3. **数据修正**: 宏观经济数据可能会被修正，滚动刷新可以确保最近 N 个月的数据是最新的。

4. **月份格式**: Handler 支持多种月份格式（YYYYMM、YYYY-MM、YYYYMMDD 等），会自动转换为 YYYYMM 格式。

## 版本历史

- **v2.0** (2025-12-23): 
  - 实现滚动刷新机制（每次运行都刷新最近 12 个月的数据）
  - 实现历史追赶机制（如果数据库落后超过 N 个月，从上次更新日期开始追赶）
  - 优化数据合并逻辑（支持多种月份格式）
  - 改进 NaN 值处理（使用 `DBService.clean_nan_in_list`）
  - 添加货币供应量数据支持（4 个 API：CPI、PPI、PMI、货币供应量）
