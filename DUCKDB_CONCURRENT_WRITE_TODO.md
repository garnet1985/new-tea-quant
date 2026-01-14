# DuckDB 并发写入问题 - TODO 清单

## 🔍 问题分析

### 核心问题
- **DuckDB 单连接写入**：DuckDB 是进程内数据库，单连接写入，不支持多线程并发写入
- **多线程 renew 操作**：`renew` 使用多线程（`FuturesWorker`），每个线程完成数据获取后立即保存
- **写锁冲突**：多个线程同时调用 `model.replace()` → `db.queue_write()` → `conn.execute()` 导致写锁冲突

### 受影响模块
1. **KlineHandler** - `after_single_task_execute` 中保存 K 线数据
2. **CorporateFinanceHandler** - `after_single_task_execute` 中保存财务数据
3. **AdjFactorEventHandler** - `after_single_task_execute` 中保存复权事件
4. **RollingHandler** - `after_normalize` 中保存宏观数据
5. **PriceIndexesHandler** - `after_normalize` 中保存价格指数
6. **StockIndexIndicatorHandler** - `after_normalize` 中保存股指指标
7. **StockIndexIndicatorWeightHandler** - `after_normalize` 中保存股指权重

---

## ✅ 已完成

- [x] **创建 BatchWriteQueue 类** (`app/core/infra/db/batch_write_queue.py`)
  - ✅ 线程安全的写入队列
  - ✅ 按表名分组收集数据
  - ✅ 达到阈值后触发批量写入
  - ✅ 超时机制（避免数据长时间不写入）
  - ✅ 支持刷新和等待写入完成
  - ✅ 日期时间类型处理
  - ✅ 批量 SQL 构建（避免 SQL 语句过长）

- [x] **集成到 DatabaseManager** (`app/core/infra/db/db_manager.py`)
  - ✅ 添加 `_write_queue` 实例
  - ✅ 修改 `queue_write` 方法使用队列
  - ✅ 添加 `flush_writes()` 和 `wait_for_writes()` 方法
  - ✅ 添加 `_direct_write()` 方法（单线程场景）
  - ✅ 添加 `get_write_stats()` 方法
  - ✅ 在 `close()` 中关闭队列

- [x] **添加配置项** (`config/database/db_config.example.json`)
  - ✅ `batch_write.batch_size`: 批量写入阈值（默认 1000）
  - ✅ `batch_write.flush_interval`: 刷新间隔（默认 5.0 秒）
  - ✅ `batch_write.enable`: 是否启用批量写入（默认 true）

- [x] **更新配置加载** (`app/core/conf/db_conf.py`)
  - ✅ 确保 `batch_write` 配置存在（使用默认值）

- [x] **修改 renew_data 完成等待** (`app/core/modules/data_source/data_source_manager.py`)
  - ✅ 在所有 handler 执行完成后等待所有写入完成

- [x] **修改 KlineHandler** (`app/core/modules/data_source/handlers/kline/handler.py`)
  - ✅ `after_all_tasks_execute` 中等待写入完成

- [x] **自动生效的模块**（无需修改）
  - ✅ 所有通过 `DbBaseModel.replace()` 保存的数据都自动使用队列
  - ✅ CorporateFinanceHandler、AdjFactorEventHandler、RollingHandler 等都已自动支持

---

## 📋 待完成

### 阶段 1：验证自动生效的模块（0.5-1 天）

#### ✅ TODO-1: 验证所有 Handler 自动支持
**说明**：所有通过 `DbBaseModel.replace()` 保存的数据都自动使用批量写入队列，无需修改代码。

**需要验证的 Handler**：
- [x] **CorporateFinanceHandler** - 已使用 `model.save_finance_data()` → `model.replace()` → `queue_write()`
- [x] **AdjFactorEventHandler** - 已使用 `model.save_events()` → `model.replace()` → `queue_write()`
- [x] **RollingHandler** - 已使用 `model.replace()` → `queue_write()`
- [x] **PriceIndexesHandler** - 已使用 `model.replace()` → `queue_write()`
- [x] **StockIndexIndicatorHandler** - 已使用 `model.replace()` → `queue_write()`
- [x] **StockIndexIndicatorWeightHandler** - 已使用 `model.replace()` → `queue_write()`

**验证步骤**：
- [ ] 运行 `python start.py renew`（多线程场景）
- [ ] 验证没有写锁错误
- [ ] 验证数据正确写入

**预计时间**：0.5 天（主要是测试）

---

### 阶段 1.5：修复其他写入方法（1-2 天）

#### TODO-1.5: 修改 `DbBaseModel.insert()` 使用批量写入队列
**文件**：`app/core/infra/db/db_base_model.py`

**问题**：
- `insert()` 方法直接使用 `cursor.executemany()`，没有走 `queue_write()`
- 在多进程/多线程场景下会导致写锁冲突

**影响模块**：
- `InvestmentDataService.save_trade()` (没有 id 时)
- `InvestmentDataService.save_operation()`
- `InvestmentDataService.save_operations_batch()`

**修改方案**：
- [ ] 修改 `insert()` 方法，使其也使用 `queue_write()`
- [ ] 需要处理 `unique_keys` 为空的情况（INSERT 不需要去重）
- [ ] 测试修改后的功能

**预计时间**：1 天

---

#### TODO-1.6: 检查 `DbBaseModel.update()` 是否需要修改
**文件**：`app/core/infra/db/db_base_model.py`

**问题**：
- `update()` 方法直接使用 `cursor.execute()`，没有走 `queue_write()`
- UPDATE 语句需要 WHERE 条件，不适合批量写入队列

**影响模块**：
- `TagScenarioModel.update()` - 更新 scenario 状态
- `MetaInfoModel.update()` - 更新元信息

**检查点**：
- [ ] 确认 `update()` 是否在多进程/多线程场景下使用
- [ ] 如果是，考虑添加队列支持或确保单进程执行
- [ ] 添加警告文档

**预计时间**：0.5 天

---

#### TODO-1.7: 检查 `TagService.batch_update_tag_definitions()`
**文件**：`app/core/modules/data_manager/data_services/stock/sub_services/tag_service.py`

**问题**：
- 直接使用 `cursor.execute()` 执行 UPDATE，没有走 `queue_write()`

**检查点**：
- [ ] 确认是否在多进程场景下使用
- [ ] 如果是，改为使用 `queue_write()` 或确保单进程执行

**预计时间**：0.5 天

---

### 阶段 2：测试和验证（1-2 天）

#### TODO-2: 功能测试（必须）
**测试内容**：
- [ ] 运行 `python start.py renew`（多线程场景）
- [ ] 验证没有写锁错误
- [ ] 验证数据正确写入
- [ ] 验证批量写入队列正常工作
- [ ] 检查写入统计信息（`db.get_write_stats()`）

**测试命令**：
```bash
# 运行 renew 操作
python start.py renew

# 检查是否有写锁错误
# 检查数据是否正确写入
```

**预计时间**：0.5 天

---

#### TODO-3: 性能测试（推荐）
**测试内容**：
- [ ] 对比启用/禁用批量写入的性能
- [ ] 测试不同 `batch_size` 的影响（500, 1000, 5000）
- [ ] 测试不同 `flush_interval` 的影响（3.0, 5.0, 10.0）
- [ ] 记录写入统计信息

**测试方法**：
```python
# 获取写入统计
stats = db.get_write_stats()
print(f"总请求数: {stats['total_requests']}")
print(f"总写入数: {stats['total_writes']}")
print(f"总行数: {stats['total_rows']}")
print(f"待写入: {stats['pending_rows']}")
```

**预计时间**：0.5 天

---

#### TODO-4: 边界情况测试（可选）
**测试内容**：
- [ ] 测试程序异常退出时队列中的数据是否丢失
- [ ] 测试大量数据写入时的内存占用
- [ ] 测试写入失败时的错误处理
- [ ] 测试并发写入压力测试

**预计时间**：0.5 天

---

### 阶段 3：优化和文档（0.5-1 天）

#### TODO-5: 优化批量写入队列（可选）
**优化点**：
- [ ] 根据实际使用情况调整默认 `batch_size`
- [ ] 优化批量 SQL 构建（当前使用字符串拼接，可考虑参数化查询）
- [ ] 添加写入性能监控和统计
- [ ] 优化内存占用（如果发现内存问题）

**预计时间**：0.5 天

---

#### TODO-6: 更新文档（可选）
**文档更新**：
- [ ] 更新 `app/core/infra/db/README.md`，说明批量写入队列
- [ ] 更新 `config/database/README.md`，说明批量写入配置
- [ ] 创建批量写入队列使用指南

**预计时间**：0.5 天

---

## 🎯 实施优先级

### 高优先级（立即执行）
1. ✅ **创建 BatchWriteQueue** - 已完成
2. ✅ **集成到 DatabaseManager** - 已完成
3. ✅ **添加配置项** - 已完成
4. ✅ **集成到业务流程** - 已完成
5. 🔄 **修改 `insert()` 方法** - **需要立即修改** ⚠️
6. 🔄 **检查 `update()` 方法** - **需要立即检查** ⚠️
7. 🔄 **功能测试** - **需要立即验证** ⚠️

### 中优先级（本周完成）
6. **性能测试** - 验证批量写入效果
7. **配置优化** - 根据实际使用调整参数

### 低优先级（可选）
8. **边界情况测试** - 测试异常情况
9. **优化和文档** - 根据测试结果优化

---

## 📊 预期效果

### 解决的问题
- ✅ **写锁冲突**：完全解决多线程并发写入问题
- ✅ **写入性能**：批量写入比单条写入更快
- ✅ **代码统一**：所有写入都通过统一的队列系统

### 性能影响
- **写入延迟**：增加 0-5 秒（等待批量收集）
- **写入性能**：提升（批量写入比单条写入快 10-100 倍）
- **内存占用**：增加（队列缓存待写入数据）

---

## ⚠️ 注意事项

1. **数据丢失风险**
   - 队列中的数据在程序崩溃时可能丢失
   - 建议在关键操作后调用 `flush_writes()` 确保数据写入

2. **配置建议**
   - **小数据量**（< 1000 条/次）：`batch_size=500, flush_interval=3.0`
   - **中等数据量**（1000-10000 条/次）：`batch_size=1000, flush_interval=5.0`（默认）
   - **大数据量**（> 10000 条/次）：`batch_size=5000, flush_interval=10.0`

3. **调试模式**
   - 设置 `batch_write.enable=false` 可以禁用批量写入，直接写入（用于调试）

---

## 🔗 相关文档

- [并发写入问题解决方案](./DUCKDB_CONCURRENT_WRITE_SOLUTION.md)
- [批量写入队列实现](./app/core/infra/db/batch_write_queue.py)
- [数据库管理器](./app/core/infra/db/db_manager.py)
- [所有数据库写入操作审计](./DUCKDB_ALL_WRITES_AUDIT.md) - **新增：完整审计报告**
