# MySQL 到 DuckDB 数据迁移指南

## 概述

`migrate_mysql_to_duckdb.py` 是一个数据迁移工具，用于将 MySQL 数据库中的数据迁移到 DuckDB。

**特性**：
- ✅ 分批迁移（避免内存溢出）
- ✅ 主键游标（避免 OFFSET 性能问题）
- ✅ 断点续传（支持中断后继续）
- ✅ 数据完整性验证（行数对比）
- ✅ 自动数据类型转换（日期、浮点数、JSON等）

## 使用方法

### 1. 基本用法（迁移所有表）

```bash
python tools/migrate_mysql_to_duckdb.py
```

### 2. 只迁移指定表

```bash
# 迁移单个表
python tools/migrate_mysql_to_duckdb.py --table stock_kline

# 迁移多个表
python tools/migrate_mysql_to_duckdb.py --table stock_kline --table stock_list
```

### 3. 调整批次大小

```bash
# 每批 50,000 行（默认 100,000）
python tools/migrate_mysql_to_duckdb.py --batch-size 50000
```

### 4. 禁用断点续传（从头开始）

```bash
python tools/migrate_mysql_to_duckdb.py --no-resume
```

### 5. 清除指定表的进度

```bash
# 清除 stock_kline 的进度，下次从头开始迁移
python tools/migrate_mysql_to_duckdb.py --clear-progress stock_kline
```

## 配置要求

### MySQL 配置

确保 `config/database/db_config.json` 中的 `base` 配置正确：

```json
{
  "base": {
    "host": "localhost",
    "user": "root",
    "password": "your_password",
    "database": "stocks-py",
    "port": 3306,
    "charset": "utf8mb4"
  }
}
```

### DuckDB 配置

确保 `config/database/db_conf.json` 中的配置正确：

```json
{
  "db_path": "data/stocks.duckdb",
  "threads": 4,
  "memory_limit": "8GB"
}
```

## 迁移流程

1. **连接数据库**：同时连接 MySQL（源）和 DuckDB（目标）
2. **获取主键**：从 schema.json 或数据库读取表的主键
3. **分批查询**：使用主键游标从 MySQL 分批读取数据
4. **数据转换**：转换日期、浮点数、JSON 等格式
5. **批量插入**：插入到 DuckDB
6. **保存进度**：记录当前主键位置（支持断点续传）
7. **验证完整性**：对比 MySQL 和 DuckDB 的记录数

## 进度文件

迁移进度保存在 `tools/migration_progress.json`：

```json
{
  "stock_kline": {
    "last_key": {
      "id": "000001.SZ",
      "term": "daily",
      "date": "20241231"
    },
    "migrated_rows": 12345678,
    "updated_at": "2026-01-13T18:00:00"
  }
}
```

如果迁移中断，下次运行时会自动从 `last_key` 继续。

## 性能建议

### 批次大小

- **小表**（< 100万行）：`--batch-size 50000` 或更小
- **中表**（100万 - 1000万行）：`--batch-size 100000`（默认）
- **大表**（> 1000万行，如 stock_kline）：`--batch-size 200000` 或更大

### 内存考虑

- 每批数据会加载到内存，批次大小 × 单行大小 ≈ 内存占用
- stock_kline 单行约 200 字节，100,000 行 ≈ 20 MB
- 建议根据可用内存调整批次大小

### 预计时间

- **小表**（< 10万行）：几秒到几十秒
- **中表**（10万 - 100万行）：几分钟
- **大表**（> 100万行，如 stock_kline 1750万行）：
  - 批次大小 100,000：约 30-60 分钟
  - 批次大小 200,000：约 20-40 分钟

## 故障排查

### 1. 连接失败

**错误**：`Can't connect to MySQL server`

**解决**：
- 检查 MySQL 服务是否运行
- 检查 `db_config.json` 中的连接配置
- 检查防火墙/网络设置

### 2. 主键获取失败

**错误**：`表 xxx 没有主键`

**解决**：
- 脚本会自动降级到简单迁移方式（使用 OFFSET）
- 对于大表，建议手动添加主键或唯一索引

### 3. 数据类型转换错误

**错误**：`Binder Error: ...`

**解决**：
- 检查 schema.json 中的字段类型定义
- 可能需要手动调整 `convert_row_to_duckdb` 方法

### 4. 记录数不一致

**警告**：`记录数不一致: MySQL=xxx, DuckDB=yyy`

**可能原因**：
- 迁移过程中 MySQL 数据发生变化
- 数据类型转换导致某些行被跳过
- 主键冲突导致插入失败

**解决**：
- 重新迁移该表：`--clear-progress TABLE_NAME` 然后重新运行
- 检查 DuckDB 日志中的错误信息

## 注意事项

1. **备份数据**：迁移前建议备份 MySQL 数据
2. **停止写入**：迁移期间建议停止对 MySQL 的写入操作
3. **磁盘空间**：确保有足够磁盘空间存储 DuckDB 文件
4. **网络稳定**：迁移大表时确保网络连接稳定
5. **定期检查**：迁移过程中可以随时中断（Ctrl+C），下次会自动继续

## 示例

### 完整迁移流程

```bash
# 1. 先迁移小表（验证流程）
python tools/migrate_mysql_to_duckdb.py --table stock_list --table meta_info

# 2. 迁移中表
python tools/migrate_mysql_to_duckdb.py --table adj_factor_event --table gdp

# 3. 最后迁移大表 stock_kline（可能需要较长时间）
python tools/migrate_mysql_to_duckdb.py --table stock_kline --batch-size 200000

# 4. 迁移剩余表
python tools/migrate_mysql_to_duckdb.py
```

### 断点续传示例

```bash
# 第一次运行（迁移到一半时中断）
python tools/migrate_mysql_to_duckdb.py --table stock_kline
# ... 中断 ...

# 第二次运行（自动从断点继续）
python tools/migrate_mysql_to_duckdb.py --table stock_kline
# 会显示：🔄 从断点继续: 已迁移 8,765,432 行，从主键 {...} 继续
```
