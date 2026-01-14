# 数据迁移完成后的下一步计划

## ✅ 已完成

- [x] 数据迁移完成（1700万+ 记录，耗时 43 分钟）
- [x] 系统已切换到 DuckDB（DatabaseManager 已实现）
- [x] 移除 ClickHouse 相关依赖和代码

---

## 🎯 下一步任务（按优先级排序）

### 阶段 1：功能验证（1-2 天）⭐⭐⭐⭐⭐

#### 1.1 基础功能测试
- [ ] **数据读取测试**
  - 测试 K 线数据查询
  - 测试股票列表查询
  - 测试标签数据查询
  - 测试复权因子查询

- [ ] **数据写入测试**
  - 测试新数据插入
  - 测试数据更新（Upsert）
  - 测试批量插入

- [ ] **关键业务流程测试**
  - 运行策略枚举：`python start.py enumerate --strategy <strategy_name>`
  - 运行数据更新：`python start.py renew`
  - 运行机会扫描：`python start.py scan --strategy <strategy_name>`

**验证标准**：
- 所有查询返回正确结果
- 数据写入成功
- 业务流程正常运行
- 无异常错误

---

### 阶段 2：性能测试与对比（1-2 天）⭐⭐⭐⭐

#### 2.1 性能基准测试
- [ ] **记录当前性能指标**
  - 运行完整策略枚举流程
  - 记录查询时间、查询次数、总耗时
  - 记录内存使用情况

- [ ] **对比 MySQL 性能（如果有历史数据）**
  - 对比查询时间
  - 对比总耗时
  - 计算性能提升倍数

**预期结果**：
- 查询时间：231.08 秒 → **< 30 秒**（7-10 倍提升）
- 总耗时：263 秒 → **< 30 秒**（9-10 倍提升）

---

### 阶段 3：查询优化（2-3 天）⭐⭐⭐⭐⭐

#### 3.1 JOIN 查询优化（最重要）
**当前问题**：
- 每只股票需要 3 次查询（K线 + 复权因子 × 2）
- 1989 只股票 = 5,967 次查询

**优化方案**：
- 使用单次 JOIN 查询替代 3 次独立查询
- 预期：5,967 次 → 1,989 次（减少 67%）

**实施位置**：
- `app/core/modules/data_manager/data_services/stock_related/stock/stock_data_service.py`
- 修改 `load_qfq_klines` 方法

**预计时间**：1-2 天

#### 3.2 批量股票处理优化
**当前问题**：
- 每个 worker 处理 1 只股票
- 1989 个 jobs，查询次数多

**优化方案**：
- 每个 worker 处理 10 只股票（批量查询）
- 使用 `IN` 查询：`WHERE id IN (?, ?, ...)`
- 预期：1,989 jobs → 199 jobs（减少 90%）

**实施位置**：
- `app/core/modules/strategy/components/opportunity_enumerator/opportunity_enumerator.py`
- `app/core/modules/strategy/components/opportunity_enumerator/enumerator_worker.py`

**预计时间**：1-2 天

---

### 阶段 4：数据完整性验证（0.5-1 天）⭐⭐⭐

#### 4.1 数据对比验证
- [ ] **记录数对比**
  - 对比每个表的记录数（MySQL vs DuckDB）
  - 确保数据完整迁移

- [ ] **关键数据抽样验证**
  - 随机抽取 100 条记录对比
  - 验证字段值一致性
  - 验证日期格式正确性

- [ ] **业务逻辑验证**
  - 运行相同策略，对比结果
  - 确保计算结果一致

---

### 阶段 5：配置和文档（1 天）⭐⭐

#### 5.1 配置文件检查
- [ ] **验证 DuckDB 配置**
  - 检查 `config/database/db_conf.json` 是否存在
  - 验证配置参数（线程数、内存限制）

- [ ] **更新配置文档**
  - 更新 `config/database/README.md`
  - 说明 DuckDB 配置项

#### 5.2 文档更新
- [ ] **更新 README.md**
  - 更新环境要求（移除 MySQL 要求）
  - 更新安装步骤
  - 更新配置说明

- [ ] **创建迁移总结文档**
  - 记录迁移过程
  - 记录性能提升数据
  - 记录遇到的问题和解决方案

---

## 📋 立即执行清单

### 今天可以做的（快速验证）

1. **快速功能测试**（30 分钟）
   ```bash
   # 测试数据读取
   python start.py scan --strategy <your_strategy>
   
   # 测试数据更新
   python start.py renew
   ```

2. **检查配置文件**（5 分钟）
   ```bash
   # 确认配置文件存在
   cat config/database/db_conf.json
   ```

3. **验证数据完整性**（10 分钟）
   ```bash
   # 检查 DuckDB 文件
   ls -lh data/stocks.duckdb
   
   # 可以写个简单脚本验证记录数
   python -c "
   import duckdb
   conn = duckdb.connect('data/stocks.duckdb')
   print('stock_kline:', conn.execute('SELECT COUNT(*) FROM stock_kline').fetchone()[0])
   print('stock_list:', conn.execute('SELECT COUNT(*) FROM stock_list').fetchone()[0])
   "
   ```

---

## 🚀 推荐执行顺序

### 第一优先级（今天/明天）
1. ✅ **功能验证** - 确保系统正常工作
2. ✅ **数据完整性检查** - 确保数据迁移正确

### 第二优先级（本周）
3. ✅ **性能测试** - 验证性能提升
4. ✅ **JOIN 查询优化** - 实现最大性能提升

### 第三优先级（下周）
5. ✅ **批量处理优化** - 进一步优化性能
6. ✅ **文档更新** - 完善文档

---

## 📊 性能优化预期

### 当前性能（迁移后，未优化）
- 查询时间：~231 秒（与 MySQL 相同，因为查询方式未变）
- 总耗时：~263 秒

### 优化后预期（JOIN + 批量处理）
- 查询时间：**~23 秒**（10 倍提升）
- 总耗时：**~28 秒**（9.4 倍提升）
- 查询次数：5,967 → **199**（30 倍减少）

---

## ⚠️ 注意事项

1. **备份数据**
   - 保留 MySQL 数据至少 1 个月
   - 定期备份 DuckDB 文件

2. **回退方案**
   - 如果遇到严重问题，可以切换回 MySQL
   - 保留 MySQL 配置和代码

3. **性能监控**
   - 记录优化前后的性能数据
   - 监控内存使用情况

---

## 🔗 相关文档

- [DuckDB 迁移 TODO](./DUCKDB_MIGRATION_TODO.md)
- [数据库优化与迁移计划](./DATABASE_OPTIMIZATION_AND_MIGRATION_PLAN.md)
- [迁移脚本使用指南](./tools/MIGRATION_README.md)
- [DuckDB 写入性能分析](./DUCKDB_WRITE_PERFORMANCE_ANALYSIS.md)

---

## 📝 更新日志

- **2026-01-13**: 数据迁移完成，创建下一步计划
