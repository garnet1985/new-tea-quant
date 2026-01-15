# 数据库配置

## 文件说明

- `db_config.json`: 实际的数据库配置文件（**不提交到 Git**）
- `db_config.example.json`: 配置文件模板（提交到 Git）
- `pg_config.json`: PostgreSQL 连接配置（迁移工具使用，**不提交到 Git**）

## 使用方法

1. 复制示例文件：
```bash
cp db_config.example.json db_config.json
```

2. 修改 `db_config.json` 中的配置（选择一种数据库）：

**PostgreSQL（推荐）**：
```json
{
  "database_type": "postgresql",
  "postgresql": {
    "host": "localhost",
    "port": 5432,
    "database": "stocks_py",
    "user": "postgres",
    "password": "your_password",
    "pool_size": 10
  }
}
```

**MySQL**：
```json
{
  "database_type": "mysql",
  "mysql": {
    "host": "localhost",
    "port": 3306,
    "database": "stocks_py",
    "user": "root",
    "password": "your_password",
    "charset": "utf8mb4"
  }
}
```

**SQLite（开发/测试）**：
```json
{
  "database_type": "sqlite",
  "sqlite": {
    "db_path": "data/stocks.db",
    "timeout": 5.0
  }
}
```

3. 配置会被 `app/core/conf/db_conf.py` 自动加载

## 配置说明

### database_type（必需）
- `postgresql`: PostgreSQL 数据库（推荐，支持多进程并发读）
- `mysql`: MySQL/MariaDB 数据库
- `sqlite`: SQLite 数据库（开发/测试环境）

### postgresql（PostgreSQL 配置）
- `host`: 数据库主机地址（默认 localhost）
- `port`: 数据库端口（默认 5432）
- `database`: 数据库名称
- `user`: 数据库用户名
- `password`: 数据库密码
- `pool_size`: 连接池大小（默认 10）

### mysql（MySQL 配置）
- `host`: 数据库主机地址（默认 localhost）
- `port`: 数据库端口（默认 3306）
- `database`: 数据库名称
- `user`: 数据库用户名
- `password`: 数据库密码
- `charset`: 字符集（默认 utf8mb4）
- `autocommit`: 是否自动提交（默认 true）

### sqlite（SQLite 配置）
- `db_path`: 数据库文件路径
- `timeout`: 超时时间（秒，默认 5.0）

### batch_write（批量写入配置）
- `enable`: 是否启用批量写入（默认 true）
- `batch_size`: 批量写入阈值（默认 1000）
- `flush_interval`: 刷新间隔（秒，默认 5.0）

### stock_list（股票列表）
- `ts_code_exclude_list`: 排除的股票代码模式（支持通配符）

## 旧配置格式兼容

系统会自动识别旧格式配置并转换：

**旧格式 1（db_path）**：
```json
{
  "db_path": "data/stocks.duckdb"
}
```
→ 自动转换为 SQLite 配置

**旧格式 2（host + database）**：
```json
{
  "host": "localhost",
  "database": "stocks_py",
  "user": "root",
  "password": "password",
  "port": 3306
}
```
→ 根据端口自动识别（3306=MySQL, 5432=PostgreSQL）

## 注意事项

- ⚠️ `db_config.json` 已添加到 `.gitignore`，不会被提交
- ✅ JSON 格式更通用，Python 原生支持
- 📝 如需添加新配置项，请同时更新 `db_config.example.json`
- 💡 可以使用 `_comment` 字段添加注释（会被程序忽略）
- 🔄 系统支持旧格式配置自动转换，无需手动迁移
