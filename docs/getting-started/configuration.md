# 配置指南

## 配置系统概述

New Tea Quant 采用**分层配置系统**，支持部分覆盖和深度合并：

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
- `database`: `new_tea_quant`

### MySQL 配置

创建 `userspace/config/database/mysql.json`：

```json
{
  "user": "root",
  "password": "your_password",
  "host": "localhost",
  "port": 3306,
  "database": "new_tea_quant"
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

## 日志配置

### 默认日志配置（logging.json）

框架的默认日志配置位于 `core/default_config/logging.json`：

```json
{
  "level": "INFO",
  "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
  "datefmt": "%Y-%m-%d %H:%M:%S",
  "_comment": "全局日志配置：可通过 userspace/config/logging.json 覆盖 level/format/datefmt",
  "module_levels": {
    "core": "INFO"
  }
}
```

- **level**: 全局默认日志级别（对应根 logger），常用值：`DEBUG` / `INFO` / `WARNING` / `ERROR`。
- **format**: 日志格式，使用标准 `logging` 格式占位符。
- **datefmt**: 时间格式。
- **module_levels**: 按模块前缀单独设置日志级别，例如：

  ```json
  {
    "module_levels": {
      "core.modules.data_source": "DEBUG",
      "core.infra.db": "INFO"
    }
  }
  ```

  上例会让数据源相关模块输出 `DEBUG`，而数据库模块仍保持 `INFO`。

### 用户自定义日志配置

要覆盖默认日志配置，在 `userspace/config/logging.json` 中只写需要修改的部分即可，例如：

```json
{
  "level": "WARNING",
  "module_levels": {
    "core.modules.data_source": "INFO",
    "core.modules.strategy": "DEBUG"
  }
}
```

- 未写入的字段会继承 `core/default_config/logging.json` 中的默认值。
- 该文件会在 CLI 入口中由 `LoggingManager.setup_logging()` 自动加载并生效。

### CLI 中开启 verbose 日志

命令行入口 `start-cli.py` 支持通过 `--verbose` 参数临时提升日志级别，用于调试：

```bash
python start-cli.py run-data-source --verbose
```

行为说明：

- 启动时先根据 `logging.json`（默认 + userspace 覆盖）初始化全局日志。
- 如果传入 `--verbose`，会将**根 logger** 动态提升到 `DEBUG` 级别，相当于“临时全局 DEBUG”，适合排查问题。

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
