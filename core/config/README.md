# 配置系统

## 📁 目录结构

```
core/config/                    # 配置文件目录（只包含 JSON 配置）
├── data.json                   # 数据配置（默认开始日期、小数位数、股票过滤等）
├── market.json                 # 市场配置（未来扩展：T+0/T+1、做空支持等）
├── system.json                 # 系统配置
├── worker.json                 # Worker 配置（任务类型、核心数等）
└── database/                   # 数据库配置
    ├── common.json             # 数据库公用配置（database_type、batch_write）
    ├── postgresql.json         # PostgreSQL 配置
    ├── mysql.json              # MySQL 配置
    ├── sqlite.json             # SQLite 配置
    └── db_conf.json            # DuckDB 配置（仅用于迁移工具）

userspace/config/               # 用户配置（可选，覆盖系统默认）
├── data.json                   # 用户数据配置
├── market.json                 # 用户市场配置
├── system.json                 # 用户系统配置
├── worker.json                 # 用户 Worker 配置
└── database/                   # 用户数据库配置
    ├── common.json             # 用户公用配置
    ├── postgresql.json         # 用户 PostgreSQL 配置（只需用户名和密码）
    ├── mysql.json              # 用户 MySQL 配置
    └── sqlite.json             # 用户 SQLite 配置
```

## 🎯 设计原则

1. **配置与逻辑分离**：`core/config/` 只包含配置文件，所有加载逻辑在 `ConfigManager` 中
2. **统一接口**：所有配置通过 `ConfigManager` 访问
3. **深度合并**：用户配置会深度合并到默认配置，不是完全替换
4. **环境变量支持**：敏感信息（如密码）可通过环境变量覆盖

## 📝 使用方式

### 便捷访问（推荐）

```python
from core.infra.project_context import ConfigManager

# 数据配置
start_date = ConfigManager.get_default_start_date()      # '20080101'
decimal_places = ConfigManager.get_decimal_places()      # 2
stock_filter = ConfigManager.get_stock_list_filter()      # {...}

# 数据库配置
db_type = ConfigManager.get_database_type()               # 'postgresql'
db_config = ConfigManager.get_database_config()          # {...}

# Worker 配置
module_config = ConfigManager.get_module_config('Simulator')  # {'task_type': ..., 'reserve_cores': ...}
```

### 完整配置

```python
from core.infra.project_context import ConfigManager

# 获取完整配置字典
data_config = ConfigManager.get_data_config()
database_config = ConfigManager.get_database_config()
market_config = ConfigManager.get_market_config()
worker_config = ConfigManager.get_worker_config()
system_config = ConfigManager.get_system_config()
```

## 🔄 配置加载优先级

1. **环境变量**（最高优先级）
   - `DB_POSTGRESQL_USER`, `DB_POSTGRESQL_PASSWORD` 等
   - 用于覆盖敏感信息

2. **userspace/config/**（用户配置）
   - 支持部分覆盖，深度合并
   - 例如：只需配置用户名和密码，其他使用默认值

3. **core/config/**（默认配置）
   - 系统默认配置

## 📋 配置示例

### 数据库配置（最简单）

**用户只需配置用户名和密码** (`userspace/config/database/postgresql.json`):
```json
{
  "user": "my_username",
  "password": "my_password"
}
```

**或使用环境变量**:
```bash
export DB_POSTGRESQL_USER=my_username
export DB_POSTGRESQL_PASSWORD=my_password
```

### 股票过滤配置

**用户配置** (`userspace/config/data.json`):
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

## 📚 相关文档

- [配置设计文档](./DESIGN.md) - 设计理念和架构说明
- [数据库配置说明](./database/README.md) - 数据库配置详细说明
