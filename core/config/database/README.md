# 数据库配置

## 📁 文件说明

- `common.json`: 数据库公用配置（database_type、batch_write）
- `postgresql.json`: PostgreSQL 配置（默认配置）
- `mysql.json`: MySQL 配置
- `sqlite.json`: SQLite 配置
- `db_conf.json`: DuckDB 配置（仅用于迁移工具）
- `*.example.json`: 配置模板文件

## 🚀 快速开始

### 方式 1: 配置文件（推荐）

**用户只需配置用户名和密码** (`userspace/config/database/postgresql.json`):
```json
{
  "user": "my_username",
  "password": "my_password"
}
```

其他配置（host、port、database 等）使用默认值。

### 方式 2: 环境变量（推荐用于生产环境）

```bash
export DB_POSTGRESQL_USER=my_username
export DB_POSTGRESQL_PASSWORD=my_password
export DB_POSTGRESQL_HOST=localhost
export DB_POSTGRESQL_PORT=5432
export DB_POSTGRESQL_DATABASE=stocks_py
```

## 📋 配置结构

### common.json（公用配置）

```json
{
  "database_type": "postgresql",
  "batch_write": {
    "enable": true,
    "batch_size": 1000,
    "flush_interval": 5.0
  }
}
```

### postgresql.json（PostgreSQL 配置）

```json
{
  "host": "localhost",
  "port": 5432,
  "database": "stocks_py",
  "user": "postgres",
  "password": "your_password_here",
  "_advanced": {
    "pool_size": 10,
    "max_connections": 100,
    "connection_timeout": 60
  }
}
```

**用户配置** (`userspace/config/database/postgresql.json`):
```json
{
  "user": "my_username",
  "password": "my_password"
}
```

### mysql.json（MySQL 配置）

```json
{
  "host": "localhost",
  "port": 3306,
  "database": "stocks_py",
  "user": "root",
  "password": "your_password_here",
  "_advanced": {
    "charset": "utf8mb4",
    "autocommit": true,
    "pool_size_min": 5,
    "pool_size_max": 30
  }
}
```

### sqlite.json（SQLite 配置）

```json
{
  "db_path": "data/stocks.db",
  "_advanced": {
    "timeout": 5.0,
    "check_same_thread": false
  }
}
```

## 🔧 配置说明

### database_type
- `postgresql`: PostgreSQL 数据库（推荐，支持多进程并发读）
- `mysql`: MySQL/MariaDB 数据库
- `sqlite`: SQLite 数据库（开发/测试环境）

### batch_write（批量写入配置）
- `enable`: 是否启用批量写入（默认 true）
- `batch_size`: 批量写入阈值（默认 1000）
- `flush_interval`: 刷新间隔（秒，默认 5.0）

### _advanced（高级配置）
高级配置放在 `_advanced` 字段中，普通用户无需配置，高级用户可以在 userspace 配置中覆盖。

## 💡 使用建议

1. **开发环境**：使用 SQLite，配置简单
2. **生产环境**：使用 PostgreSQL，通过环境变量配置敏感信息
3. **简化配置**：用户只需配置用户名和密码，其他使用默认值
4. **高级配置**：如需调整连接池等高级参数，在 userspace 配置中覆盖

## 📝 注意事项

- ⚠️ 配置文件中的密码不会被提交到 Git（已添加到 `.gitignore`）
- ✅ 推荐使用环境变量配置敏感信息
- 📝 如需添加新配置项，请同时更新对应的 `.example.json` 文件
- 💡 可以使用 `_comment` 字段添加注释（会被程序忽略）

