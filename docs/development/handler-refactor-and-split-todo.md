# Handler 重构与分表 TODO

本文档列出了完成 handler 重构和 kline/daily_basic 分表的所有待办任务。

## 阶段1：Handler 重构收尾工作

### 1.1 ConfigManager 命名统一
- [ ] **统一 ConfigManager 方法命名为 `load_xxx_config`**
  - 当前状态：存在 `load_xxx_config` 和 `get_xxx_config` 两种命名
  - 需要修改的方法：
    - `get_data_config()` → `load_data_config()` (已存在，需要统一调用)
    - `get_database_config()` → `load_database_config()` (已存在，需要统一调用)
    - `get_market_config()` → `load_market_config()`
    - `get_worker_config()` → `load_worker_config()`
    - `get_system_config()` → `load_system_config()`
  - 影响范围：所有调用这些方法的地方
  - 文件：`core/infra/project_context/config_manager.py`

### 1.2 移除 dry_run 概念
- [ ] **清理 README 文档中的 dry_run 引用**
  - 文件：
    - `userspace/data_source/handlers/price_indexes/README.md`
    - `userspace/data_source/handlers/kline/README.md`
    - `userspace/data_source/handlers/corporate_finance/README.md`
    - `userspace/data_source/handlers/adj_factor_event/README.md`
  - 操作：删除所有 `dry_run` 相关的文档说明

### 1.3 Handler 简化检查
- [ ] **检查所有 handler 是否已使用新的简化方法**
  - 已简化的 handler（已验证）：
    - ✅ `lpr/handler.py` - 已简化
    - ✅ `gdp/handler.py` - 已简化
    - ✅ `shibor/handler.py` - 已简化
    - ✅ `price_indexes/handler.py` - 已简化
    - ✅ `stock_index_indicator/handler.py` - 已简化
    - ✅ `stock_index_indicator_weight/handler.py` - 已简化
    - ✅ `latest_trading_date/handler.py` - 已简化
  - 需要检查的 handler：
    - [ ] `kline/handler.py` - 复杂，需要检查是否可以使用新方法
    - [ ] `corporate_finance/handler.py` - 复杂，需要检查是否可以使用新方法
    - [ ] `adj_factor_event/handler.py` - 复杂，需要检查是否可以使用新方法
    - [ ] `stock_list/handler.py` - 需要检查是否可以使用新方法

### 1.4 Handler 钩子函数优化
- [ ] **检查各 handler 的钩子函数是否还有简化空间**
  - `on_after_normalize`：所有 handler 应该都简化为 `return normalized_data`（基类已自动清洗 NaN）
  - `on_after_mapping`：检查是否还有可以内置到基类的日期标准化逻辑
  - `on_after_fetch`：检查是否还有可以配置化的数据重组逻辑

---

## 阶段2：Kline/Daily Basic 分表（方案3）

### 2.1 数据库 Schema 设计
- [ ] **创建 `stock_daily_basic` 表**
  - 表结构设计：
    - 主键：`(id, date)` 复合主键
    - 字段：`pe`, `pb`, `ps`, `dv_ttm`, `turnover_rate`, `volume_ratio`, `total_mv`, `circ_mv` 等
    - 索引：`(id, date)` 主键索引，`date` 单列索引
  - 文件：`core/modules/data_manager/models/stock/daily_basic_model.py` (新建)
  - Schema 文件：`userspace/data_source/handlers/daily_basic/schema.py` (新建)

- [ ] **修改 `stock_kline` 表 Schema**
  - 移除所有 daily_basic 相关字段（pe, pb, ps 等）
  - 保留：`id`, `date`, `term`, `open`, `close`, `high`, `low`, `volume`, `amount` 等价格和成交量字段
  - 文件：`userspace/data_source/handlers/kline/schema.py`

### 2.2 创建 Daily Basic Handler
- [ ] **创建 `daily_basic_handler`**
  - 文件：`userspace/data_source/handlers/daily_basic/handler.py` (新建)
  - 功能：
    - 只处理 daily_basic API
    - 只更新指标字段到 `stock_daily_basic` 表
    - 使用 rolling 更新策略（滚动刷新最近30天）
    - 配置：`renew_mode: "rolling"`, `rolling_unit: "day"`, `rolling_length: 30`
  - 配置：`userspace/data_source/handlers/daily_basic/config.json` (新建)

- [ ] **创建 Daily Basic Service**
  - 文件：`core/modules/data_manager/services/stock/daily_basic_service.py` (新建)
  - 功能：
    - 提供 daily_basic 数据的查询接口
    - 支持按股票+日期范围查询
    - 支持 JOIN kline 数据的便捷方法

### 2.3 简化 Kline Handler
- [ ] **移除 daily_basic 相关逻辑**
  - 移除 `_merge_kline_and_basic` 方法
  - 移除 `get_daily_basic` API Job 创建逻辑
  - 移除 daily_basic 数据合并逻辑
  - 只保留 K 线数据（daily/weekly/monthly）的处理
  - 文件：`userspace/data_source/handlers/kline/handler.py`

- [ ] **更新 Kline Handler 配置**
  - 移除 `apis.get_daily_basic` 配置
  - 更新 `on_before_fetch` 逻辑，只创建 3 个 API Job（daily/weekly/monthly kline）
  - 文件：`userspace/data_source/handlers/kline/config.json`

### 2.4 数据访问层重构
- [ ] **更新 `KlineService`**
  - 修改查询方法，支持 JOIN `stock_daily_basic` 表
  - 提供便捷方法：`load_with_basic()` - 同时获取 K 线和指标数据
  - 保持向后兼容：现有方法继续工作，但指标字段从 JOIN 获取
  - 文件：`core/modules/data_manager/services/stock/kline_service.py`

- [ ] **更新 `StockService`**
  - 修改 `load_with_latest_price()` 方法，使用 JOIN 获取指标数据
  - 文件：`core/modules/data_manager/services/stock/stock_service.py`

- [ ] **更新 `StrategyWorkerDataManager`**
  - 修改数据加载逻辑，使用 JOIN 获取指标数据（如果需要）
  - 文件：`core/modules/strategy/components/strategy_worker_data_manager.py`

- [ ] **更新 `TagWorkerDataManager`**
  - 修改数据加载逻辑，使用 JOIN 获取指标数据（如果需要）
  - 文件：`core/modules/tag/core/models/tag_worker_data_manager.py`

### 2.5 数据迁移
- [ ] **编写数据迁移脚本**
  - 从 `stock_kline` 表提取 daily_basic 字段数据
  - 插入到新的 `stock_daily_basic` 表
  - 从 `stock_kline` 表删除 daily_basic 字段
  - 文件：`scripts/migrate_kline_daily_basic_split.py` (新建)

- [ ] **数据一致性检查**
  - 验证迁移后数据完整性
  - 验证 JOIN 查询结果正确性
  - 验证现有查询逻辑正常工作

### 2.6 并发写入处理
- [ ] **实现 Upsert 机制**
  - Kline handler 和 daily_basic handler 可能同时写入
  - 需要确保按主键合并，不冲突
  - Kline handler：写入 `stock_kline` 表
  - Daily_basic handler：写入 `stock_daily_basic` 表
  - 两个表独立，无需处理并发冲突

### 2.7 文档更新
- [ ] **更新 Handler README**
  - `userspace/data_source/handlers/kline/README.md` - 移除 daily_basic 相关说明
  - `userspace/data_source/handlers/daily_basic/README.md` - 新建文档

- [ ] **更新架构文档**
  - 更新数据流文档，说明分表后的数据获取流程
  - 更新查询模式文档，说明 JOIN 使用方式

---

## 阶段3：测试与验证

### 3.1 单元测试
- [ ] **测试 Daily Basic Handler**
  - 测试数据获取
  - 测试数据保存
  - 测试 rolling 更新策略

- [ ] **测试 Kline Handler**
  - 测试简化后的数据获取
  - 测试数据保存（不包含 daily_basic）

- [ ] **测试数据访问层**
  - 测试 JOIN 查询
  - 测试向后兼容性

### 3.2 集成测试
- [ ] **测试完整数据流**
  - Kline handler 和 daily_basic handler 独立运行
  - 验证数据正确写入各自表
  - 验证 JOIN 查询返回正确结果

- [ ] **测试策略和标签**
  - 验证策略查询正常工作
  - 验证标签查询正常工作
  - 验证指标数据正确获取

---

## 执行顺序建议

1. **先完成阶段1（Handler 重构收尾）**
   - 1.1 ConfigManager 命名统一
   - 1.2 移除 dry_run 概念
   - 1.3 Handler 简化检查
   - 1.4 Handler 钩子函数优化

2. **然后执行阶段2（分表）**
   - 2.1 数据库 Schema 设计
   - 2.2 创建 Daily Basic Handler
   - 2.3 简化 Kline Handler
   - 2.4 数据访问层重构
   - 2.5 数据迁移
   - 2.6 并发写入处理
   - 2.7 文档更新

3. **最后执行阶段3（测试与验证）**
   - 3.1 单元测试
   - 3.2 集成测试

---

## 注意事项

1. **向后兼容性**：分表后需要确保现有查询逻辑正常工作，可能需要添加兼容层
2. **性能考虑**：JOIN 查询可能影响性能，需要添加适当的索引
3. **数据一致性**：分表后可能出现有 K 线没指标的情况，需要在查询时处理 NULL 值
4. **迁移风险**：数据迁移需要谨慎，建议先在测试环境验证
