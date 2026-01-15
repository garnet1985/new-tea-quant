# DuckDB 到 PostgreSQL 迁移指南

## 📋 概述

本指南说明如何将数据从 DuckDB 迁移到 PostgreSQL。

## ✅ 前置条件

1. **PostgreSQL 已安装并运行**
   - 验证：运行 `python3 tools/verify_postgresql_connection.py`
   - 如果失败，请参考 `POSTGRESQL_READY.md`

2. **已安装依赖**
   ```bash
   pip install psycopg2-binary duckdb
   ```

3. **配置文件已就绪**
   - PostgreSQL 配置：`config/database/pg_config.json`
   - DuckDB 配置：`config/database/db_conf.json`（自动从代码加载）

## 🔍 步骤 1: 验证 PostgreSQL 连接

在开始迁移前，先验证 PostgreSQL 连接是否正常：

```bash
python3 tools/verify_postgresql_connection.py
```

**预期输出**：
- ✅ 连接成功
- ✅ PostgreSQL 版本信息
- ✅ 基本操作测试通过

如果验证失败，请检查：
1. PostgreSQL 服务是否运行
2. 配置文件中的连接信息是否正确
3. 用户权限是否足够

## 📦 步骤 2: 执行数据迁移

### 推荐方式：分阶段迁移（先小表，后 stock_kline）

**推荐使用分阶段迁移**，先迁移小表，最后迁移大数据量的 `stock_kline` 表：

```bash
# 方式 1: 使用便捷脚本（推荐）
python3 tools/migrate_small_tables_first.py
```

这个脚本会：
1. 先迁移所有小表（使用默认批量大小 10000）
2. 最后迁移 `stock_kline` 表（使用批量大小 500000）

### 方式 2: 使用主迁移脚本

```bash
# 先迁移小表（排除 stock_kline）
python3 tools/migrate_duckdb_to_postgresql.py --exclude-tables stock_kline

# 然后迁移 stock_kline（使用大批量）
python3 tools/migrate_duckdb_to_postgresql.py --tables stock_kline --kline-batch-size 1000000
```

### 方式 3: 一次性迁移所有表

```bash
python3 tools/migrate_duckdb_to_postgresql.py --kline-batch-size 500000
```

脚本会自动：
1. 从 `config/database/db_conf.json` 读取 DuckDB 路径
2. 从 `config/database/pg_config.json` 读取 PostgreSQL 配置
3. 创建所有表结构
4. 先迁移小表，最后迁移 `stock_kline`（如果使用 `--exclude-tables`）

### 高级选项

```bash
# 指定 DuckDB 路径
python3 tools/migrate_duckdb_to_postgresql.py --duckdb-path /path/to/stocks.duckdb

# 指定 PostgreSQL 配置文件
python3 tools/migrate_duckdb_to_postgresql.py --pg-config /path/to/pg_config.json

# 调整默认批量插入大小（默认 10000）
python3 tools/migrate_duckdb_to_postgresql.py --batch-size 5000

# 调整 stock_kline 的批量大小（默认 1000000）
python3 tools/migrate_duckdb_to_postgresql.py --kline-batch-size 1000000

# 只迁移指定的表
python3 tools/migrate_duckdb_to_postgresql.py --tables stock_kline stock_list

# 排除某些表（会最后迁移）
python3 tools/migrate_duckdb_to_postgresql.py --exclude-tables stock_kline
```

### 迁移过程

迁移脚本会执行以下步骤：

1. **连接数据库**
   - 连接 DuckDB（只读模式）
   - 连接 PostgreSQL

2. **创建表结构**
   - 读取所有 schema 定义
   - 在 PostgreSQL 中创建对应的表
   - 创建索引

3. **迁移数据（分阶段）**
   - **阶段 1：迁移小表**
     - 批量插入（默认每批 10000 条）
     - 使用 `ON CONFLICT` 处理重复数据
   - **阶段 2：迁移大表（如 stock_kline）**
     - 批量插入（默认每批 500000 条，可配置）
     - 使用 `ON CONFLICT` 处理重复数据

4. **验证数据**
   - 对比记录数
   - 生成迁移报告

### 批量大小说明

- **小表**：默认批量大小 10000 条/批
- **stock_kline**：默认批量大小 1000000 条/批（100万条，可通过 `--kline-batch-size` 调整）

**为什么 stock_kline 使用更大的批量？**
- `stock_kline` 表通常包含大量数据（可能数百万到数千万条）
- 使用更大的批量可以减少数据库往返次数，提高迁移速度
- 100万条/批意味着：1000万条数据只需要 10 次读取和 10 次插入
- 如果遇到内存问题，可以适当减小批量大小（如 500000）

### 迁移报告

迁移完成后，会生成 `migration_report.json` 文件，包含：
- 迁移时间戳
- 每个表的迁移结果
- 总记录数统计
- 成功/失败/跳过的表数量

## 🔧 故障排除

### 问题 1: 连接失败

**错误**：`psycopg2.OperationalError: connection refused`

**解决方案**：
1. 检查 PostgreSQL 服务是否运行
2. 检查配置文件中的 host、port 是否正确
3. 检查防火墙设置

### 问题 2: 权限不足

**错误**：`permission denied` 或 `must be owner`

**解决方案**：
1. 确保 PostgreSQL 用户有创建表的权限
2. 可能需要使用 `postgres` 超级用户

### 问题 3: 表已存在

**错误**：`relation already exists`

**解决方案**：
- 脚本使用 `CREATE TABLE IF NOT EXISTS`，不会报错
- 如果表已存在且有数据，会使用 `ON CONFLICT` 更新

### 问题 4: 数据类型不兼容

**错误**：`invalid input syntax for type`

**解决方案**：
- 检查 schema 定义是否正确
- 某些 DuckDB 类型可能需要手动转换

## 📊 迁移后验证

### 1. 检查表数量

```sql
SELECT COUNT(*) FROM information_schema.tables 
WHERE table_schema = 'public';
```

### 2. 检查数据量

```sql
-- 示例：检查 stock_kline 表
SELECT COUNT(*) FROM stock_kline;

-- 检查每个表的记录数
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
ORDER BY table_name;
```

### 3. 抽样验证

```sql
-- 随机抽样几条数据
SELECT * FROM stock_kline LIMIT 10;
```

## 🚀 下一步

迁移完成后，可以：

1. **更新应用配置**：修改代码使用 PostgreSQL 适配器
2. **测试应用**：确保所有功能正常
3. **性能测试**：对比 DuckDB 和 PostgreSQL 的性能
4. **备份数据**：保留 DuckDB 数据作为备份

## 📚 相关文档

- `POSTGRESQL_READY.md` - PostgreSQL 设置指南
- `POSTGRESQL_MIGRATION_PLAN.md` - 迁移计划
- `POSTGRESQL_MIGRATION_CHECKLIST.md` - 迁移检查清单

## ⚠️ 注意事项

1. **备份数据**：迁移前建议备份 DuckDB 数据库
2. **测试环境**：建议先在测试环境验证
3. **数据量**：大数据量迁移可能需要较长时间
4. **索引**：迁移后检查索引是否正常创建
5. **外键**：如果 schema 中有外键约束，需要确保顺序正确

## 💡 提示

- 迁移过程中可以随时中断（Ctrl+C），已迁移的数据不会丢失
- 可以多次运行迁移脚本，会使用 `ON CONFLICT` 更新已存在的数据
- 如果某个表迁移失败，可以单独迁移该表：`--tables table_name`
