# 配置指南

## 配置系统概述

Stocks-Py 采用**分层配置系统**，支持部分覆盖和深度合并：

1. **环境变量**（最高优先级）
2. **userspace/config/**（用户配置）
3. **core/default_config/**（系统默认配置）

用户配置会**深度合并**到系统默认配置，而不是完全替换。这意味着您只需配置需要修改的部分。

## 数据库配置

### PostgreSQL 配置（推荐）

创建 `userspace/config/database/postgresql.json`：

```json
{
  "user": "my_username",
  "password": "my_password"
}
```

其他配置（host、port、database 等）使用系统默认值：
- `host`: `localhost`
- `port`: `5432`
- `database`: `stocks_py`

### MySQL 配置

创建 `userspace/config/database/mysql.json`：

```json
{
  "user": "root",
  "password": "your_password",
  "host": "localhost",
  "port": 3306,
  "database": "stocks_py"
}
```

### SQLite 配置

创建 `userspace/config/database/sqlite.json`：

```json
{
  "db_path": "data/stocks.db"
}
```

### 使用环境变量

也可以通过环境变量配置：

```bash
# PostgreSQL
export DB_POSTGRESQL_USER=my_username
export DB_POSTGRESQL_PASSWORD=my_password

# MySQL
export DB_MYSQL_USER=root
export DB_MYSQL_PASSWORD=your_password
```

### 切换数据库类型

创建 `userspace/config/database/common.json`：

```json
{
  "database_type": "mysql"
}
```

可选值：`postgresql`、`mysql`、`sqlite`

## 数据配置

### 股票过滤配置

创建 `userspace/config/data.json`：

```json
{
  "stock_list_filter": {
    "exclude_patterns": {
      "start_with": {
        "id": ["688", "8"]
      }
    }
  }
}
```

只配置需要修改的部分，其他过滤规则使用系统默认值。

## 完整配置示例

### 最小配置（只配置数据库）

```json
// userspace/config/database/postgresql.json
{
  "user": "postgres",
  "password": "your_password"
}
```

### 完整配置示例

参考 `userspace/config/` 目录下的 `.example.json` 文件。

## 配置验证

配置加载后，系统会自动验证配置的有效性。如果配置有误，会在启动时显示错误信息。

## 相关文档

- [安装指南](installation.md)
- [用户配置目录说明](../../userspace/config/README.md)
- [数据库模块文档](../../core/infra/db/README.md)
