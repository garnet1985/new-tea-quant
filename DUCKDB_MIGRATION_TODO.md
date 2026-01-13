# DuckDB 迁移 TODO 清单

本文档记录了将 stocks-py 应用从 MySQL 迁移到 DuckDB 的详细任务清单。

**目标**：实现 9-10 倍性能提升，简化部署（零配置单文件数据库）

**参考文档**：
- 详细迁移计划：`DATABASE_OPTIMIZATION_AND_MIGRATION_PLAN.md`
- DuckDB 官方文档：https://duckdb.org/docs/

---

## 📋 任务清单

### 阶段 1：准备阶段

#### ✅ TODO-1: 准备阶段
**任务**：安装 DuckDB 依赖，创建迁移分支，准备测试数据

**详细步骤**：
- [ ] 安装 DuckDB：`pip install duckdb`
- [ ] 创建迁移分支：`git checkout -b feature/duckdb-migration`
- [ ] 准备测试数据（小数据集，用于验证功能）
- [ ] 研究 DuckDB 文档和最佳实践
- [ ] 记录当前 MySQL 性能基准（用于后续对比）

**预计时间**：1-2 天

---

### 阶段 2：核心数据库层

#### ✅ TODO-2: 创建 DuckDBDatabaseManager
**任务**：实现基本连接、查询、事务管理

**文件**：`app/core/infra/db/duckdb_manager.py`

**功能要求**：
- [ ] 实现 `__init__()`：初始化数据库连接（单文件）
- [ ] 实现 `initialize()`：创建连接，配置性能参数（线程数、内存限制）
- [ ] 实现 `execute_sync_query()`：执行查询，返回字典列表
- [ ] 实现 `get_connection()`：获取连接（兼容现有接口）
- [ ] 实现 `close()`：关闭连接
- [ ] 实现事务支持（`transaction()` 上下文管理器）
- [ ] 添加错误处理和日志

**参考接口**：参考 `DatabaseManager` 的接口设计，保持兼容

**预计时间**：1-2 天

---

#### ✅ TODO-3: 创建 Schema 适配器
**任务**：实现 MySQL 到 DuckDB 的字段类型映射和 CREATE TABLE SQL 生成

**文件**：`app/core/infra/db/duckdb_schema_adapter.py`

**功能要求**：
- [ ] 定义字段类型映射字典：
  - `VARCHAR` → `VARCHAR`
  - `TEXT` → `VARCHAR`
  - `INT` → `INTEGER`
  - `BIGINT` → `BIGINT`
  - `FLOAT` → `DOUBLE`
  - `DOUBLE` → `DOUBLE`
  - `TINYINT(1)` → `BOOLEAN`
  - `DATETIME` → `TIMESTAMP`
  - `DATE` → `DATE`
  - `JSON` → `JSON`
- [ ] 实现 `convert_mysql_schema_to_duckdb()`：转换 schema 定义
- [ ] 实现 `generate_duckdb_create_table_sql()`：生成 CREATE TABLE SQL
- [ ] 处理主键（DuckDB 支持）
- [ ] 处理索引（DuckDB 不支持传统索引，需要特殊处理或忽略）
- [ ] 处理字段约束（NOT NULL, DEFAULT 等）

**预计时间**：1-2 天

---

#### ✅ TODO-4: 创建 SQL 兼容层
**任务**：实现日期函数映射、占位符转换、Upsert 语法转换

**文件**：`app/core/infra/db/duckdb_sql_adapter.py`

**功能要求**：
- [ ] 实现占位符转换：`%s` → `?`
- [ ] 实现日期函数映射：
  - `STR_TO_DATE()` → `CAST()`
  - `CURDATE()` → `CURRENT_DATE`
  - `NOW()` → `CURRENT_TIMESTAMP`
  - `DATE_SUB()` → `DATE_SUB`（DuckDB 支持）
- [ ] 实现 Upsert 语法转换：
  - `ON DUPLICATE KEY UPDATE` → `INSERT OR REPLACE` 或 `ON CONFLICT DO UPDATE`
- [ ] 实现 `convert_mysql_sql_to_duckdb()`：主转换函数
- [ ] 处理其他 MySQL 特定语法（如 `LIMIT` 偏移量语法）

**预计时间**：1-2 天

---

#### ✅ TODO-5: 创建数据库适配器
**任务**：支持 MySQL 和 DuckDB 双模式切换

**文件**：`app/core/infra/db/db_adapter.py`

**功能要求**：
- [ ] 定义 `DatabaseType` 枚举（MYSQL, DUCKDB）
- [ ] 实现 `DatabaseAdapter` 类：
  - 根据配置选择数据库类型
  - 统一接口（`initialize()`, `execute_sync_query()`, `get_connection()` 等）
  - 支持配置切换（迁移期间可随时回退）
- [ ] 保持与现有 `DatabaseManager` 接口兼容
- [ ] 添加配置验证和错误处理

**预计时间**：1-2 天

---

### 阶段 3：配置和集成

#### ✅ TODO-6: 更新配置文件
**任务**：添加 DuckDB 配置选项，支持数据库类型选择

**文件**：`config/database/db_config.example.json`

**配置项**：
- [ ] 添加 `database_type` 字段（"mysql" 或 "duckdb"）
- [ ] 添加 `duckdb` 配置块：
  ```json
  {
    "db_path": "data/stocks.duckdb",
    "threads": 4,
    "memory_limit": "8GB"
  }
  ```
- [ ] 保留 `base` 配置块（MySQL 配置，用于迁移脚本）
- [ ] 更新配置说明文档

**预计时间**：0.5 天

---

#### ✅ TODO-7: 更新 DbSchemaManager
**任务**：支持生成 DuckDB 的 CREATE TABLE SQL，处理索引差异

**文件**：`app/core/infra/db/db_schema_manager.py`

**修改点**：
- [ ] 修改 `generate_create_table_sql()`：根据数据库类型选择生成器
- [ ] 集成 `duckdb_schema_adapter.py` 的功能
- [ ] 处理索引差异（DuckDB 不支持传统索引，需要警告或忽略）
- [ ] 保持向后兼容（MySQL 模式仍正常工作）

**预计时间**：1 天

---

#### ✅ TODO-8: 更新 DbBaseModel
**任务**：适配 DuckDB 的 SQL 语法，处理连接池差异

**文件**：`app/core/infra/db/db_base_model.py`

**修改点**：
- [ ] 修改 `replace()` 方法：根据数据库类型选择 Upsert 语法
  - MySQL: `ON DUPLICATE KEY UPDATE`
  - DuckDB: `INSERT OR REPLACE` 或 `ON CONFLICT DO UPDATE`
- [ ] 修改 `execute_sync_query()`：处理占位符转换（`%s` → `?`）
- [ ] 处理连接池差异（DuckDB 无需连接池，直接使用连接）
- [ ] 保持所有 CRUD 方法兼容

**预计时间**：1-2 天

---

#### ✅ TODO-9: 更新 DataManager
**任务**：支持选择数据库类型，初始化时根据配置创建对应的数据库管理器

**文件**：`app/core/modules/data_manager/data_manager.py`

**修改点**：
- [ ] 修改 `__init__()`：读取配置，选择数据库类型
- [ ] 修改 `initialize()`：根据配置创建 `DatabaseManager` 或 `DuckDBDatabaseManager`
- [ ] 使用 `DatabaseAdapter` 统一接口
- [ ] 保持 DataService 接口不变（业务层无需修改）
- [ ] 添加数据库类型切换的日志

**预计时间**：1 天

---

### 阶段 4：数据迁移

#### ✅ TODO-10: 创建数据迁移脚本
**任务**：从 MySQL 导出数据，转换格式，导入到 DuckDB，验证数据完整性

**文件**：`tools/migrate_mysql_to_duckdb.py`

**功能要求**：
- [ ] 连接 MySQL 和 DuckDB
- [ ] 读取所有基础表的 schema
- [ ] 分批导出数据（每批 10,000 条，避免内存溢出）
- [ ] 数据格式转换：
  - 日期时间格式
  - 浮点数精度
  - NULL 值处理
  - JSON 字段
- [ ] 批量导入到 DuckDB
- [ ] 数据完整性验证：
  - 记录数对比
  - 关键字段校验和
  - 主键唯一性检查
- [ ] 生成迁移报告
- [ ] 支持断点续传（迁移失败后可继续）

**需要迁移的表**（17 个）：
- stock_kline, stock_list, adj_factor_event
- gdp, lpr, shibor, corporate_finance, price_indexes
- investment_trades, investment_operations
- tag_definition, tag_scenario, tag_value
- system_cache, stock_index_indicator, stock_index_indicator_weight, meta_info

**预计时间**：1-2 天

---

### 阶段 5：性能优化

#### ✅ TODO-11: 实现 JOIN 查询优化
**任务**：修改 StockDataService.load_qfq_klines，使用单次 JOIN 查询替代 3 次独立查询

**文件**：`app/core/modules/data_manager/data_services/stock_related/stock/stock_data_service.py`

**优化方案**：
- [ ] 当前实现：3 次查询
  1. `_load_raw_klines`: SELECT * FROM stock_kline WHERE ...
  2. `_load_factor_events`: SELECT * FROM adj_factor_event WHERE ...
  3. `_get_latest_factor`: SELECT * FROM adj_factor_event WHERE ... ORDER BY ... LIMIT 1
- [ ] 优化实现：1 次 JOIN 查询
  - 使用窗口函数或相关子查询
  - 适配 DuckDB 语法（可能使用 LATERAL JOIN 或窗口函数）
- [ ] 保持接口不变（业务层无需修改）
- [ ] 添加性能对比日志

**性能预期**：
- 查询次数：5,967 → 1,989（减少 67%）
- 查询时间：231.08 秒 → ~77 秒（约 3 倍提升，DuckDB 可能更快）

**预计时间**：1-2 天

---

#### ✅ TODO-12: 实现批量股票处理
**任务**：修改 OpportunityEnumerator 和 EnumeratorWorker，支持批量查询多只股票

**文件**：
- `app/core/modules/strategy/components/opportunity_enumerator/opportunity_enumerator.py`
- `app/core/modules/strategy/components/opportunity_enumerator/enumerator_worker.py`

**优化方案**：
- [ ] 修改 `OpportunityEnumerator`：
  - 支持批量股票分组（每批 10 只，可配置）
  - 动态计算批量大小（根据可用内存）
- [ ] 修改 `EnumeratorWorker`：
  - 实现 `load_batch_qfq_klines()`：批量加载多只股票的 K 线
  - 使用 IN 查询：`WHERE id IN (?, ?, ...)`
  - 按股票分组处理数据
- [ ] 内存控制：
  - 根据可用内存动态调整批量大小
  - 监控内存使用情况
- [ ] 保持接口兼容（支持单只股票模式）

**性能预期**：
- Jobs 数量：1,989 → 199（减少 90%，10只/Worker）
- 查询次数：5,967 → 597（减少 90%）
- 查询时间：231.08 秒 → ~23 秒（约 10 倍提升）

**预计时间**：2-3 天

---

### 阶段 6：测试和验证

#### ✅ TODO-13: 测试所有基础表
**任务**：验证每个表的 schema 转换、数据迁移、CRUD 操作

**测试内容**：
- [ ] Schema 转换测试：
  - 验证所有字段类型映射正确
  - 验证主键创建正确
  - 验证约束（NOT NULL, DEFAULT）正确
- [ ] 数据迁移测试：
  - 验证所有表的数据完整迁移
  - 验证记录数一致
  - 验证关键字段值一致
- [ ] CRUD 操作测试：
  - INSERT：单条和批量插入
  - SELECT：条件查询、排序、分页
  - UPDATE：单条和批量更新
  - DELETE：条件删除
  - REPLACE/Upsert：插入或更新
- [ ] 时序数据特有操作测试：
  - `load_latest_date()`：获取最新日期
  - `load_latest_records()`：获取每个分组的最新记录
  - `load_first_records()`：获取每个分组的最早记录

**需要测试的表**（17 个）：
1. stock_kline
2. stock_list
3. adj_factor_event
4. gdp
5. lpr
6. shibor
7. corporate_finance
8. price_indexes
9. investment_trades
10. investment_operations
11. tag_definition
12. tag_scenario
13. tag_value
14. system_cache
15. stock_index_indicator
16. stock_index_indicator_weight
17. meta_info

**预计时间**：2-3 天

---

#### ✅ TODO-14: 性能测试
**任务**：对比 MySQL vs DuckDB 的查询性能，验证达到预期提升

**测试场景**：
- [ ] 单表查询性能：
  - 简单条件查询
  - 复杂条件查询（多条件 AND/OR）
  - 排序查询
  - 分页查询
- [ ] JOIN 查询性能：
  - 2 表 JOIN
  - 3 表 JOIN
  - 窗口函数查询
- [ ] 批量操作性能：
  - 批量插入（1,000 / 10,000 / 100,000 条）
  - 批量更新
  - 批量 Upsert
- [ ] 完整流程性能：
  - 策略枚举流程（1989 只股票）
  - 记录查询时间、查询次数、内存使用
- [ ] 不同数据量下的性能：
  - 小数据集（100 只股票）
  - 中等数据集（500 只股票）
  - 大数据集（1989 只股票）

**性能指标**：
- 查询时间
- 查询次数
- 内存使用
- CPU 使用率

**预期结果**：
- 查询时间：231.08 秒 → ~2 秒（115 倍提升）
- 总耗时：263 秒 → ~28 秒（9.4 倍提升）
- 查询次数：5,967 → 199（30 倍减少）

**预计时间**：2-3 天

---

#### ✅ TODO-15: 集成测试
**任务**：运行完整的策略枚举流程，验证功能正确性

**测试内容**：
- [ ] 数据加载测试：
  - 验证所有数据服务正常工作
  - 验证 K 线数据加载正确
  - 验证复权因子计算正确
- [ ] 策略枚举测试：
  - 运行完整的策略枚举流程
  - 验证机会和目标的生成正确
  - 验证结果文件输出正确
- [ ] 边界情况测试：
  - 空数据表
  - 缺失数据
  - 异常数据格式
  - 并发访问
- [ ] 回退测试：
  - 验证可以切换回 MySQL
  - 验证数据一致性

**预计时间**：2-3 天

---

### 阶段 7：文档和部署

#### ✅ TODO-16: 更新文档
**任务**：更新 README、数据库配置说明、迁移指南

**文档更新**：
- [ ] 更新 `README.md`：
  - 添加 DuckDB 说明
  - 更新安装步骤
  - 更新配置说明
- [ ] 更新 `config/database/README.md`：
  - 添加 DuckDB 配置说明
  - 添加数据库类型选择说明
- [ ] 创建迁移指南 `MIGRATION_GUIDE.md`：
  - 迁移步骤
  - 数据迁移脚本使用说明
  - 常见问题解答
  - 回退方案
- [ ] 更新 `DATABASE_OPTIMIZATION_AND_MIGRATION_PLAN.md`：
  - 标记已完成的任务
  - 记录实际性能提升数据

**预计时间**：1-2 天

---

#### ✅ TODO-17: 更新 requirements.txt
**任务**：添加 duckdb 依赖，保留 pymysql 和 DBUtils

**修改内容**：
- [ ] 添加 `duckdb` 依赖（指定版本）
- [ ] 保留 `pymysql` 和 `DBUtils`（用于迁移脚本和回退）
- [ ] 更新依赖说明注释

**预计时间**：0.5 天

---

#### ✅ TODO-18: 更新 .gitignore
**任务**：添加 DuckDB 数据库文件路径

**修改内容**：
- [ ] 添加 DuckDB 数据库文件路径：
  - `data/*.duckdb`
  - `data/*.duckdb.wal`（WAL 文件）
  - `*.duckdb`（根目录下的数据库文件）
- [ ] 添加迁移临时文件：
  - `tools/migration_*.log`
  - `tools/migration_*.json`

**预计时间**：0.5 天

---

## 📊 进度跟踪

### 总体进度
- **总任务数**：18 个
- **预计总时间**：20-30 天
- **当前状态**：待开始

### 阶段进度
- [ ] 阶段 1：准备阶段（1-2 天）
- [ ] 阶段 2：核心数据库层（5-8 天）
- [ ] 阶段 3：配置和集成（3-4 天）
- [ ] 阶段 4：数据迁移（1-2 天）
- [ ] 阶段 5：性能优化（3-5 天）
- [ ] 阶段 6：测试和验证（6-9 天）
- [ ] 阶段 7：文档和部署（2-3 天）

---

## 🔄 依赖关系

```
TODO-1 (准备)
  ↓
TODO-2 (DuckDBDatabaseManager)
  ↓
TODO-3 (Schema 适配器) ──┐
  ↓                      │
TODO-4 (SQL 兼容层) ──────┤
  ↓                      │
TODO-5 (数据库适配器) ────┘
  ↓
TODO-6 (配置文件) ────┐
  ↓                  │
TODO-7 (DbSchemaManager) ──┐
  ↓                        │
TODO-8 (DbBaseModel) ──────┤
  ↓                        │
TODO-9 (DataManager) ──────┘
  ↓
TODO-10 (数据迁移脚本)
  ↓
TODO-11 (JOIN 优化) ──┐
  ↓                  │
TODO-12 (批量处理) ───┘
  ↓
TODO-13 (表测试) ──┐
  ↓               │
TODO-14 (性能测试) ─┤
  ↓               │
TODO-15 (集成测试) ─┘
  ↓
TODO-16 (文档) ──┐
  ↓             │
TODO-17 (requirements) ─┤
  ↓             │
TODO-18 (gitignore) ────┘
```

---

## ⚠️ 注意事项

### 数据安全
- 迁移前必须完整备份 MySQL 数据
- 验证数据完整性后再删除 MySQL 数据
- 保留原始数据文件至少 1 个月

### 回退方案
- 保留 MySQL 支持（通过配置切换）
- 迁移期间可以随时回退到 MySQL
- 确保配置切换简单可靠

### 性能验证
- 迁移前记录 MySQL 性能基准
- 迁移后对比 DuckDB 性能
- 确保达到预期提升（9-10 倍）

### 测试覆盖
- 所有基础表必须测试
- 所有 CRUD 操作必须测试
- 完整业务流程必须测试
- 边界情况必须测试

---

## 📝 更新日志

- **2026-01-XX**：创建 TODO 清单文档

---

## 🔗 相关文档

- [详细迁移计划](./DATABASE_OPTIMIZATION_AND_MIGRATION_PLAN.md)
- [数据库架构文档](./app/core/infra/db/README.md)
- [DuckDB 官方文档](https://duckdb.org/docs/)
