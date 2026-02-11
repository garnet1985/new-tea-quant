# Config 模块概览

> **快速入门指南**：本文档介绍配置系统的整体用途、目录结构和配置机制。  
> 具体「如何加载与合并配置」的实现细节，位于 `infra/project_context` 下的配置管理组件文档。

---

## 模块简介

**Config 模块**（`core/default_config` + `userspace/config`）只负责提供**配置文件本身**，不包含任何 Python 代码。  
它本身几乎没有业务逻辑，只解决一个问题：

> 在不同环境（本地 / 线上）下，用尽量少的用户配置，安全、稳定地拿到框架所需的所有配置。

### 核心职责

- **提供默认配置**：`core/default_config/` 提供框架级默认配置
- **提供用户覆盖层**：`userspace/config/` 提供项目级用户覆盖配置
- **定义配置结构**：约定 data/system/worker/database/market 等配置文件的字段与含义
- **支持三层配置机制**：默认配置 + 用户配置 + 环境变量（由基础设施配置管理组件负责具体加载与合并）

### 不负责的事情

- ❌ 不直接参与任何业务逻辑（扫描、回测、交易等）
- ❌ 不负责数据库连接 / 初始化（交给 `db` 模块）
- ❌ 不负责路径解析、项目根目录发现（交给 `project_context` 模块）
- ❌ 不实现「如何读文件、如何合并、如何暴露 API」——这些由 Infra 层的配置管理组件实现

---

## 目录结构（核心 + 用户）

### 核心配置：`core/default_config/`

```text
core/default_config/            # 默认配置（只包含 JSON）
├── data.json                   # 数据配置（开始日期、小数位数、股票过滤等）
├── market.json                 # 市场配置（为未来扩展预留）
├── system.json                 # 系统级配置
├── worker.json                 # Worker 配置（任务类型、核心数等）
├── logging.json                # 日志配置（全局 level/format 以及按模块覆盖）
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
├── logging.json                # 用户日志配置（覆盖默认 logging.json 的部分字段）
└── database/
    ├── common.json             # 用户数据库公共配置（如 database_type）
    ├── postgresql.json         # 用户 PostgreSQL 配置（通常只需 user/password）
    ├── mysql.json              # 用户 MySQL 配置
    └── sqlite.json             # 用户 SQLite 配置
```

> **约定**：所有实际生效的 `*.json` 文件都**不提交到 Git**，仓库中只保留 `*.example.json` 作为模板（模板说明详见 `core/default_config/README.md` 与 `userspace/config/README.md`）。

---

## 配置机制与优先级（概念层）

整体优先级从高到低如下（后者是默认 / 回退）：

1. **环境变量**
   - 典型变量：`DB_POSTGRESQL_USER`、`DB_POSTGRESQL_PASSWORD` 等
   - 只用于覆盖敏感字段或少数关键开关
2. **`userspace/config/` 用户配置**
   - 支持**深度合并**，只需要写你想改的那一小块
3. **`core/default_config/` 默认配置**
   - 项目内置的安全默认值

---

## 典型场景示例（只描述「怎么写 JSON」）

### 1. 最简数据库配置（PostgreSQL）

用户只需要在 `userspace/config/database/postgresql.json` 中写：

```json
{
  "user": "my_username",
  "password": "my_password"
}
```

其余字段（`host` / `port` / `database` / 连接池等）全部继承自 `core/default_config/database/postgresql.json`。

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

> 上述示例只描述「**配置文件怎么写**」。  
> 具体「在代码中如何读取这些配置」的 API，请参考 `infra/project_context` 下的配置管理文档。

---

## 与其他模块的关系

- **与 `project_context`（配置管理实现）**：
  - `project_context` 下的配置管理组件负责查找项目根目录、定位配置路径、加载并合并配置
  - Config 模块只是提供「静态 JSON 配置文件」
- **与 `db` 模块**：
  - `db` 通过配置管理组件获取数据库连接参数
  - Config 不负责真正的数据库连接
- **与业务模块（strategy / data_source / worker 等）**：
  - 业务模块通过配置管理组件读取自己需要的配置段，而不是直接读 JSON 文件

---

## 相关文档

- **[architecture.md](./architecture.md)**：配置系统架构与设计细节（站在「配置文件」视角）
- **[decisions.md](./decisions.md)**：关键设计决策记录
- **`core/default_config/README.md`**：核心默认配置说明
- **`userspace/config/README.md`**：用户配置说明
- **`infra/project_context` 架构文档**：配置管理组件与 ConfigManager 的实现与用法说明

---

**文档结束**

