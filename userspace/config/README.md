# 用户配置目录

## 📁 目录结构

```
userspace/config/               # 用户配置目录（可选）
├── data.json                  # 用户数据配置（可选）
├── market.json                # 用户市场配置（可选）
├── system.json                # 用户系统配置（可选）
├── worker.json                # 用户 Worker 配置（可选）
└── database/                  # 用户数据库配置（可选）
    ├── common.json            # 用户公用配置（可选）
    ├── postgresql.json        # 用户 PostgreSQL 配置（可选）
    ├── mysql.json             # 用户 MySQL 配置（可选）
    └── sqlite.json            # 用户 SQLite 配置（可选）
```

## 🎯 设计理念

### 部分覆盖原则

用户配置会**深度合并**到系统默认配置，而不是完全替换。这意味着：

- ✅ **只需配置需要修改的部分**：其他配置使用系统默认值
- ✅ **支持部分覆盖**：可以只修改配置的某个字段
- ✅ **保持配置完整性**：系统会自动合并用户配置和默认配置

### 配置优先级

1. **环境变量**（最高优先级）
2. **userspace/config/**（用户配置）
3. **core/default_config/**（系统默认配置）

## 🚀 快速开始

### 1. 数据库配置（最简单）

**PostgreSQL 配置** (`userspace/config/database/postgresql.json`):
```json
{
  "user": "my_username",
  "password": "my_password"
}
```

其他配置（host、port、database 等）使用系统默认值。

**或使用环境变量**:
```bash
export DB_POSTGRESQL_USER=my_username
export DB_POSTGRESQL_PASSWORD=my_password
```

### 2. 股票过滤配置

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

只配置需要修改的部分，其他过滤规则使用系统默认值。

### 3. 数据库类型切换

**切换数据库类型** (`userspace/config/database/common.json`):
```json
{
  "database_type": "mysql"
}
```

然后配置对应的数据库连接信息（`mysql.json`）。

## 📋 配置示例

### data.json

**完整示例** (`userspace/config/data.example.json`):
```json
{
  "stock_list_filter": {
    "exclude_patterns": {
      "start_with": {
        "id": ["688", "8"],
        "name": ["*ST", "ST"]
      }
    }
  }
}
```

**说明**：
- 只需配置需要修改的部分
- 其他配置（如 `default_start_date`、`decimal_places`）使用系统默认值

### database/common.json

**完整示例** (`userspace/config/database/common.example.json`):
```json
{
  "database_type": "postgresql"
}
```

**说明**：
- 用于切换数据库类型
- 如果使用默认的 PostgreSQL，可以不配置

### database/postgresql.json

**完整示例** (`userspace/config/database/postgresql.example.json`):
```json
{
  "postgresql": {
    "user": "my_username",
    "password": "my_password"
  }
}
```

**说明**：
- 只需配置用户名和密码（放在 `postgresql` wrapper 内）
- 其他配置（host、port、database、连接池等）使用系统默认值
- 高级用户可以在 userspace 配置中覆盖高级参数

### database/mysql.json

**完整示例** (`userspace/config/database/mysql.example.json`):
```json
{
  "mysql": {
    "user": "my_username",
    "password": "my_password"
  }
}
```

### database/sqlite.json

**完整示例** (`userspace/config/database/sqlite.example.json`):
```json
{
  "sqlite": {
    "db_path": "data/my_stocks.db"
  }
}
```

## 💡 使用建议

### 1. 开发环境

使用 SQLite，配置简单：
```json
// userspace/config/database/common.json
{
  "database_type": "sqlite"
}

// userspace/config/database/sqlite.json
{
  "sqlite": {
    "db_path": "data/dev_stocks.db"
  }
}
```

### 2. 生产环境

使用 PostgreSQL，通过环境变量配置敏感信息：
```bash
export DB_POSTGRESQL_USER=production_user
export DB_POSTGRESQL_PASSWORD=secure_password
export DB_POSTGRESQL_HOST=db.example.com
export DB_POSTGRESQL_PORT=5432
export DB_POSTGRESQL_DATABASE=stocks_prod
```

### 3. 高级配置

如需调整连接池等高级参数，在 userspace 配置中覆盖：
```json
// userspace/config/database/postgresql.json
{
  "postgresql": {
    "user": "my_username",
    "password": "my_password",
    "_advanced": {
      "pool_size": 20,
      "max_connections": 200
    }
  }
}
```

## 📝 注意事项

- ⚠️ **配置文件不会被提交到 Git**：所有 `*.json` 文件已添加到 `.gitignore`
- ✅ **使用 `.example.json` 作为模板**：复制 example 文件并重命名为 `.json`
- 💡 **支持 `_comment` 字段**：可以在配置中添加注释（会被程序忽略）
- 🔄 **配置热重载**：修改配置后需要重启应用才能生效

## 🔗 相关文档

- [核心默认配置说明](../../core/default_config/README.md) - 系统默认配置说明
- [配置设计文档](../../core/default_config/DESIGN.md) - 配置系统设计理念
- [数据库配置详细说明](../../core/default_config/database/README.md) - 数据库配置详细说明
