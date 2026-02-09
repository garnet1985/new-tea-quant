# Handler 钩子函数使用情况分析

本文档分析 userspace 中所有 data source handler 的钩子函数使用情况，识别重复模式和简化机会。

## 钩子函数概览

### 1. `on_before_fetch` - 抓取前阶段

**用途**：在 API 调用前修改或扩展 `ApiJob` 列表

#### 使用模式

**模式 A：为实体列表（股票/指数）扩展 ApiJob**
- **Handler**: `kline`, `adj_factor_event`, `corporate_finance`, `stock_index_indicator`, `stock_index_indicator_weight`
- **行为**：
  - 从 `context` 获取实体列表（`stock_list` 或 `index_list`）
  - 查询数据库获取每个实体的最新更新日期
  - 根据增量更新逻辑筛选需要更新的实体
  - 为每个实体创建多个 `ApiJob`（每个 API 一个）
  - 注入实体 ID 和日期范围参数
- **示例**：
  ```python
  # kline: 为每个股票创建 4 个 ApiJob (daily/weekly/monthly/daily_basic)
  # adj_factor_event: 为每个股票创建 3 个 ApiJob (adj_factor/daily_kline/qfq_kline)
  # corporate_finance: 为每个股票创建 1 个 ApiJob
  # stock_index_indicator: 为每个指数和周期创建 ApiJob
  # stock_index_indicator_weight: 为每个指数创建 1 个 ApiJob
  ```

**模式 B：设置 context 数据**
- **Handler**: `stock_list`
- **行为**：设置 `last_update` 到 context（用于后续添加字段）

**模式 C：动态设置日期范围**
- **Handler**: `latest_trading_date`
- **行为**：根据配置的 `backward_checking_days` 计算日期范围并注入到所有 `ApiJob`

**模式 D：自定义日期范围计算**
- **Handler**: `corporate_finance` (使用 `on_calculate_date_range`)
- **行为**：
  - 查询数据库获取每个股票的最新财报季度
  - 实现滚动批次逻辑（分批更新股票）
  - 返回 per-stock 日期范围字典

#### 重复逻辑识别

1. **数据库查询最新日期**：
   - `kline`: `_query_stock_latest_dates` - 查询每个股票在 3 个周期的最新日期
   - `stock_index_indicator_weight`: 查询每个指数的最新权重日期
   - `adj_factor_event`: `_get_last_updated_dates` - 查询每个股票的最后更新日期
   - `corporate_finance`: 查询每个股票的最新财报季度

2. **增量更新判断**：
   - `kline`: 检查周线/月线的时间间隔（至少 1 周/1 个月）
   - `stock_index_indicator_weight`: 检查至少 30 天才更新
   - `adj_factor_event`: 检查超过阈值才更新

3. **ApiJob 扩展**：
   - 所有模式 A 的 handler 都有类似的循环创建 `ApiJob` 的逻辑

---

### 2. `on_after_fetch` - 抓取后阶段

**用途**：在数据抓取完成后，将原始结果转换为统一的 `fetched_data` 格式

#### 使用模式

**模式 A：调用基类 + 添加业务字段**
- **Handler**: `stock_index_indicator`, `stock_index_indicator_weight`
- **行为**：
  1. 调用 `super().on_after_fetch()` 让基类按 `group_by` 分组
  2. 使用 `normalization_helper.result_to_records` 转换原始结果
  3. 使用 `add_constant_fields`（或等价逻辑）添加业务字段（如 `id`, `term`）
  4. 返回统一格式 `{api_name: {entity_id: records}}`
- **示例**：
  ```python
  # stock_index_indicator: 添加 id (指数代码) 和 term (daily/weekly/monthly)
  # stock_index_indicator_weight: 添加 id (指数代码)
  ```

**模式 B：不覆盖（使用基类默认）**
- **Handler**: `lpr`, `shibor`, `gdp`, `price_indexes`, `stock_list`, `latest_trading_date`, `kline`, `adj_factor_event`, `corporate_finance`
- **行为**：基类根据 `group_by` 配置自动分组，或使用 `_unified` 格式

#### 重复逻辑识别

- **添加常量字段**：`stock_index_indicator` 和 `stock_index_indicator_weight` 都使用 `add_constant_fields` 添加 `id` 字段

---

### 3. `on_after_mapping` - 字段映射后阶段

**用途**：在应用 `field_mapping` 后，对记录列表进行进一步处理

#### 使用模式

**模式 A：日期标准化 + 过滤 + 类型转换**
- **Handler**: `stock_index_indicator`, `stock_index_indicator_weight`, `latest_trading_date`
- **行为**：
  1. 使用 `normalization_helper.normalize_date_field` 标准化日期格式
  2. 使用 `self.filter_records_by_required_fields` 过滤缺少必需字段的记录
  3. 使用 `self.ensure_float_field` 确保数值字段为 float 类型
- **示例**：
  ```python
  # stock_index_indicator: normalize_date_field + filter_records_by_required_fields
  # stock_index_indicator_weight: normalize_date_field + filter_records_by_required_fields + ensure_float_field
  # latest_trading_date: DateUtils.to_yyyymmdd + 筛选交易日 + 提取最新日期
  ```

**模式 B：添加业务字段 + 设置默认值 + 过滤**
- **Handler**: `stock_list`
- **行为**：
  1. 从 `context` 获取 `last_update`
  2. 为每条记录添加 `last_update` 和 `is_active` 字段
  3. 设置默认值（`industry`, `type`, `exchange_center`）
  4. 过滤无效记录（必须有 `id` 和 `name`）

**模式 C：自定义月份标准化 + 设置默认值**
- **Handler**: `price_indexes`
- **行为**：
  1. 自定义 `_normalize_month` 方法标准化月份格式为 `YYYYMM`
  2. 为所有字段设置默认值（`cpi`, `ppi`, `pmi`, `m0`, `m1`, `m2` 等）
  3. 按日期排序

**模式 D：不覆盖（使用基类默认）**
- **Handler**: `lpr`, `shibor`, `gdp`, `kline`, `adj_factor_event`, `corporate_finance`

#### 重复逻辑识别

1. **日期标准化**：
   - `stock_index_indicator`, `stock_index_indicator_weight`: 使用 `normalize_date_field`
   - `latest_trading_date`: 使用 `DateUtils.to_yyyymmdd`
   - `price_indexes`: 自定义 `_normalize_month`（月份格式）

2. **记录过滤**：
   - `stock_index_indicator`, `stock_index_indicator_weight`: 使用 `filter_records_by_required_fields`
   - `stock_list`: 手动过滤（必须有 `id` 和 `name`）

3. **类型转换**：
   - `stock_index_indicator_weight`: 使用 `ensure_float_field` 确保 `weight` 为 float

4. **设置默认值**：
   - `stock_list`: 手动设置 `industry`, `type`, `exchange_center` 默认值
   - `price_indexes`: 手动设置所有数值字段默认值为 `0.0`

---

### 4. `on_after_normalize` - 标准化后阶段

**用途**：在数据标准化后，进行最终的数据清洗

#### 使用模式

**模式 A：清洗 NaN 值**
- **Handler**: `lpr`, `shibor`, `gdp`, `price_indexes`, `stock_index_indicator`, `stock_index_indicator_weight`
- **行为**：调用 `self.clean_nan_in_normalized_data(normalized_data, default=xxx)` 并返回
- **默认值**：
  - `lpr`, `shibor`, `gdp`: `default=None`
  - `price_indexes`, `stock_index_indicator`, `stock_index_indicator_weight`: `default=0.0`

**模式 B：直接返回（不做处理）**
- **Handler**: `stock_list`, `latest_trading_date`, `kline`, `adj_factor_event`, `corporate_finance`
- **行为**：直接返回 `normalized_data`，不做任何处理

#### 重复逻辑识别

- **NaN 清洗**：6 个 handler 都使用 `clean_nan_in_normalized_data`，只是 `default` 值不同

---

### 5. `on_after_execute_single_api_job` - 单个 API 执行后

**用途**：在单个 `ApiJob` 执行完成后立即处理数据（执行期保存）

#### 使用模式

**模式 A：按股票保存企业财务数据**
- **Handler**: `corporate_finance`
- **行为**：
  1. 从 `fetched_data` 提取该 `ApiJob` 的结果
  2. 调用 `_normalize_single_stock_data` 标准化数据
  3. 调用 `data_manager.stock.corporate_finance.save_batch` 保存数据
  4. 记录日志

#### 重复逻辑识别

- **数据标准化**：`_normalize_single_stock_data` 内部使用 `self.clean_nan_in_records` 和 `DateUtils.date_to_quarter`

---

### 6. `on_after_execute_job_batch_for_single_stock` - 单个股票批次执行后

**用途**：在单个股票的 `ApiJobBatch` 执行完成后立即处理数据（执行期保存）

#### 使用模式

**模式 A：按股票保存 K 线数据**
- **Handler**: `kline`
- **行为**：
  1. 调用 `_process_fetched_data_by_stock` 按股票分组处理数据
  2. 合并 K 线数据和 `daily_basic` 数据
  3. 调用 `self.clean_nan_in_records` 清洗 NaN
  4. 调用 `data_manager.stock.kline.save` 保存数据
  5. 使用 `_saved_stocks` 集合避免重复保存

**模式 B：按股票保存复权因子事件**
- **Handler**: `adj_factor_event`
- **行为**：
  1. 从 `fetched_data` 按 `job_id` 提取每个股票的数据
  2. 调用 `_save_stock_adj_factor_events` 处理并保存
  3. 内部逻辑：
     - 删除该股票的旧复权事件记录
     - 解析三个 API 的结果（`adj_factor`, `daily_kline`, `qfq_kline`）
     - 计算复权因子事件并保存
     - 生成 CSV 文件（如果需要）

#### 重复逻辑识别

- **按股票分组**：两个 handler 都需要从 `fetched_data` 中按 `job_id` 提取股票数据
- **数据清洗**：`kline` 使用 `self.clean_nan_in_records`

---

### 7. `_normalize_data` - 私有标准化方法（已废弃）

**用途**：部分 handler 复写了此私有方法（不推荐）

#### 使用情况

- **Handler**: `kline`, `corporate_finance`, `adj_factor_event`
- **状态**：这些 handler 复写了 `_normalize_data`，但根据新的设计，应该使用钩子函数而不是复写私有方法

---

## 总结：重复模式和简化机会

### 高频重复操作

1. **日期标准化**（6 个 handler）
   - `normalize_date_field` / `DateUtils.to_yyyymmdd` / `_normalize_month`
   - **建议**：统一使用 `normalization_helper.normalize_date_field`，支持更多日期格式

2. **记录过滤**（3 个 handler）
   - `filter_records_by_required_fields`
   - **建议**：已统一，继续使用

3. **NaN 清洗**（9 个 handler）
   - `clean_nan_in_records` / `clean_nan_in_normalized_data`
   - **建议**：已统一，继续使用

4. **类型转换**（1 个 handler）
   - `ensure_float_field`
   - **建议**：已统一，继续使用

5. **添加常量字段**（2 个 handler）
   - `add_constant_fields`
   - **建议**：已统一，继续使用

6. **数据库查询最新日期**（4 个 handler）
   - 每个 handler 都有自己的查询逻辑
   - **建议**：考虑提供通用的查询辅助方法（但需要知道表结构，可能不太通用）

7. **增量更新判断**（3 个 handler）
   - 每个 handler 都有自己的判断逻辑（时间间隔、阈值等）
   - **建议**：考虑提供通用的时间间隔判断辅助方法

8. **ApiJob 扩展**（5 个 handler）
   - 为实体列表创建多个 `ApiJob` 的模式很相似
   - **建议**：考虑提供通用的 `ApiJob` 扩展辅助方法（但每个 handler 的业务逻辑不同，可能不太通用）

### 简化建议

1. **统一日期标准化**：
   - `price_indexes` 的 `_normalize_month` 可以迁移到 `normalization_helper` 或专门的日期 helper，支持月份格式
   - `latest_trading_date` 的日期提取逻辑可以简化

2. **统一默认值设置**：
   - `stock_list` 和 `price_indexes` 的默认值设置逻辑可以抽象为辅助方法

3. **统一记录过滤**：
   - `stock_list` 的手动过滤可以改为使用 `filter_records_by_required_fields`

4. **执行期保存模式**：
   - `kline`, `adj_factor_event`, `corporate_finance` 的执行期保存逻辑是业务特定的，保留即可
   - 但可以考虑统一数据提取和分组的辅助方法

5. **移除 `_normalize_data` 复写**：
   - `kline`, `corporate_finance`, `adj_factor_event` 应该移除对 `_normalize_data` 的复写，改用钩子函数

---

## 钩子函数使用统计

| 钩子函数 | 使用数量 | Handler 列表 |
|---------|---------|-------------|
| `on_before_fetch` | 7 | kline, adj_factor_event, corporate_finance, stock_index_indicator, stock_index_indicator_weight, stock_list, latest_trading_date |
| `on_after_fetch` | 2 | stock_index_indicator, stock_index_indicator_weight |
| `on_after_mapping` | 5 | stock_index_indicator, stock_index_indicator_weight, stock_list, price_indexes, latest_trading_date |
| `on_after_normalize` | 11 | 所有 handler |
| `on_after_execute_single_api_job` | 1 | corporate_finance |
| `on_after_execute_job_batch_for_single_stock` | 2 | kline, adj_factor_event |
| `on_calculate_date_range` | 1 | corporate_finance |
| `_normalize_data` (私有) | 3 | kline, corporate_finance, adj_factor_event |

---

## 下一步行动

1. **统一日期标准化**：扩展 `normalization_helper.normalize_date_field` 支持月份格式
2. **统一默认值设置**：添加 `set_default_values` 辅助方法
3. **简化 `stock_list`**：使用 `filter_records_by_required_fields` 替代手动过滤
4. **移除 `_normalize_data` 复写**：重构 `kline`, `corporate_finance`, `adj_factor_event` 使用钩子函数
5. **统一执行期数据提取**：考虑添加通用的按实体分组辅助方法
