# Config 模块概览

> **快速入门指南**：本文档介绍配置系统的整体用途、目录结构和常用用法。详细设计请参考 [architecture.md](./architecture.md)。

---

## 模块简介

**Config 模块**负责整套「配置文件 → 加载 → 合并 → 对外暴露」的机制，它本身几乎没有业务逻辑，只解决一个问题：

> 在不同环境（本地 / 线上）下，用尽量少的用户配置，安全、稳定地拿到框架所需的所有配置。

### 核心职责

- **统一配置入口**：所有配置都通过 `ConfigManager` 访问，而不是在各处直接读 JSON 文件
- **核心 / 用户配置分层**：`core/config/` 提供默认配置，`userspace/config/` 提供用户覆盖
- **深度合并**：用户配置只需要写「差异」，其余均继承默认配置
- **环境变量覆盖敏感信息**：账号、密码等敏感字段优先从环境变量读取

### 不负责的事情

- ❌ 不直接参与任何业务逻辑（扫描、回测、交易等）
- ❌ 不负责数据库连接 / 初始化（交给 `db` 模块）
- ❌ 不负责路径解析、项目根目录发现（交给 `project_context` 模块）

---

## 目录结构（核心 + 用户）

### 核心配置：`core/config/`

```text
core/config/                    # 默认配置（只包含 JSON）
├── data.json                   # 数据配置（开始日期、小数位数、股票过滤等）
├── market.json                 # 市场配置（为未来扩展预留）
├── system.json                 # 系统级配置
├── worker.json                 # Worker 配置（任务类型、核心数等）
└── database/                   # 数据库配置
    ├── common.json             # 公共配置（database_type、batch_write 等）
    ├── postgresql.json         # PostgreSQL 默认配置
    ├── mysql.json              # MySQL 默认配置
    ├── sqlite.json             # SQLite 默认配置
    └── db_conf.json            # DuckDB / 迁移工具相关
```

### 用户配置：`userspace/config/`

```text
userspace/config/               # 用户覆盖配置（可选）
├── data.json                   # 用户数据配置
├── market.json                 # 用户市场配置
├── system.json                 # 用户系统配置
├── worker.json                 # 用户 Worker 配置
└── database/
    ├── common.json             # 用户数据库公共配置（如 database_type）
    ├── postgresql.json         # 用户 PostgreSQL 配置（通常只需 user/password）
    ├── mysql.json              # 用户 MySQL 配置
    └── sqlite.json             # 用户 SQLite 配置
```

> **约定**：所有实际生效的 `*.json` 文件都**不提交到 Git**，仓库中只保留 `*.example.json` 作为模板。

---

## 配置加载优先级

整体优先级从高到低如下（后者是默认 / 回退）：

1. **环境变量**
   - 典型变量：`DB_POSTGRESQL_USER`、`DB_POSTGRESQL_PASSWORD` 等
   - 只用于覆盖敏感字段或少数关键开关
2. **`userspace/config/` 用户配置**
   - 支持**深度合并**，只需要写你想改的那一小块
3. **`core/config/` 默认配置**
   - 项目内置的安全默认值

---

## 常见使用方式（入口：`ConfigManager`）

Config 模块本身只有 JSON 文件，真正的访问入口在 `project_context` 下的 `ConfigManager`。

### 便捷访问（推荐）

```python
from core.infra.project_context import ConfigManager

# 数据配置
start_date = ConfigManager.get_default_start_date()      # 如: '20080101'
decimal_places = ConfigManager.get_decimal_places()      # 小数位数
stock_filter = ConfigManager.get_stock_list_filter()     # 股票过滤规则

# 数据库配置
db_type = ConfigManager.get_database_type()              # 'postgresql' / 'mysql' / 'sqlite'
db_conf = ConfigManager.get_database_config()            # 完整数据库配置 dict

# Worker 配置（例如 Simulator）
simulator_conf = ConfigManager.get_module_config('Simulator')
```

### 原始配置字典

```python
from core.infra.project_context import ConfigManager

data_conf = ConfigManager.get_data_config()
database_conf = ConfigManager.get_database_config()
market_conf = ConfigManager.get_market_config()
worker_conf = ConfigManager.get_worker_config()
system_conf = ConfigManager.get_system_config()
```

---

## 典型场景示例

### 1. 最简数据库配置（PostgreSQL）

用户只需要在 `userspace/config/database/postgresql.json` 中写：

```json
{
  "user": "my_username",
  "password": "my_password"
}
```

其余字段（`host` / `port` / `database` / 连接池等）全部继承自 `core/config/database/postgresql.json`。

也可以用环境变量替代：

```bash
export DB_POSTGRESQL_USER=my_username
export DB_POSTGRESQL_PASSWORD=my_password
```

### 2. 切换数据库类型

```json
// userspace/config/database/common.json
{
  "database_type": "mysql"
}
```

随后再在 `userspace/config/database/mysql.json` 里补充必要字段即可。

### 3. 股票过滤规则

```json
// userspace/config/data.json
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

只配置自己关心的部分，其余数据配置（开始日期、小数位数等）继续使用默认值。

---

## 与其他模块的关系

- **与 `project_context`**：
  - `project_context.ConfigManager` 负责查找项目根目录、定位配置路径、加载并合并配置
  - Config 模块只是提供「静态 JSON 配置文件」
- **与 `db` 模块**：
  - `db` 通过 `ConfigManager.get_database_config()` 获取数据库连接参数
  - Config 不负责真正的数据库连接
- **与业务模块（strategy / data_source / worker 等）**：
  - 业务模块通过 `ConfigManager` 读取自己需要的配置段

---

## 相关文档

- **[architecture.md](./architecture.md)**：配置系统架构与设计细节
- **[decisions.md](./decisions.md)**：关键设计决策记录
- **`core/config/README.md`**：核心配置说明
- **`userspace/config/README.md`**：用户配置说明

---

**文档结束**

