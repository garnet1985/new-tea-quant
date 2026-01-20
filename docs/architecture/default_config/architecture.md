# Config 架构文档

**版本：** 3.0  
**最后更新**：2026-01-20

---

## 目录

- [业务背景与目标](#业务背景与目标)
- [设计目标](#设计目标)
- [整体架构](#整体架构)
- [核心组件与职责](#核心组件与职责)
- [配置加载机制（概念层）](#配置加载机制概念层)
- [未来扩展方向](#未来扩展方向)

---

## 业务背景与目标

### 问题与痛点

在早期版本中，配置相关的问题主要体现在：

1. **配置分散**：配置数据和加载逻辑混在各个模块中，难以维护和排查问题
2. **覆盖机制粗糙**：用户配置一旦存在，就完全替换默认配置，无法「只改一部分」
3. **数据库配置复杂**：要连接一个数据库，需要写一大堆参数，对普通用户不友好
4. **配置 vs 数据混淆**：例如指数列表等「数据枚举」曾被当作配置管理

### 业务目标

围绕上述问题，Config 模块的业务目标是：

1. **降低配置门槛**：让普通用户用最少的配置跑通系统（尤其是数据库）
2. **统一配置入口**：所有模块通过统一接口获取配置，避免各自读文件
3. **安全地处理敏感信息**：支持用环境变量覆盖账号密码等字段
4. **区分配置与业务数据**：配置只放「控制行为」的内容，数据枚举放到业务模块

---

## 设计目标

基于业务目标，配置系统在技术上有以下设计目标：

1. **配置与逻辑彻底分离**
   - `core/default_config/` 只放 JSON 文件，不放任何 Python 代码
   - 所有加载、合并、校验逻辑由 Infra 层的配置管理组件统一处理（实现位于 `infra/project_context`，不在本模块内）
2. **深度合并（partial override）**
   - 用户只写需要覆盖的那一小块，其余自动继承默认配置
3. **多层来源统一建模**
   - 默认配置（core）+ 用户配置（userspace）+ 环境变量（env）→ 一套统一结构
4. **语义化访问接口**
   - 除了「拿整棵 dict」外，提供高频场景的便捷方法（如 `get_default_start_date`）
5. **可演进性**
   - 预留 `market.json` 等文件用于未来扩展（多市场、多交易规则）

---

## 整体架构

### 目录与分层

```text
core/default_config/             # 默认配置（只包含 JSON）
├── data.json                    # 数据配置
├── market.json                  # 市场配置（预留）
├── system.json                  # 系统配置
├── worker.json                  # Worker 配置
└── database/
    ├── common.json              # 数据库公共配置（database_type 等）
    ├── postgresql.json          # PostgreSQL 默认配置
    ├── mysql.json               # MySQL 默认配置
    ├── sqlite.json              # SQLite 默认配置
    └── db_conf.json             # DuckDB / 迁移工具配置

userspace/config/                # 用户覆盖配置（可选）
├── data.json
├── market.json
├── system.json
├── worker.json
└── database/
    ├── common.json
    ├── postgresql.json
    ├── mysql.json
    └── sqlite.json
```

### 高层关系图（概念）

```text
        环境变量 (ENV)
              ▲
              │ 覆盖敏感字段
              │
 userspace/config/*.json          core/default_config/*.json
        ▲                                  ▲
        │ 深度合并                         │
        └───────────────┬─────────────────┘
                        ▼
        配置管理组件（位于 Infra / Project Context）
                        │
                        ▼
        各业务模块（db / worker / strategy / data_source / ...）
```

---

## 核心组件与职责

> Config 模块自身没有 Python 代码，本节只从「配置文件」视角描述职责；  
> 具体加载与合并逻辑由 Infra 层的配置管理组件实现（见 `infra/project_context` 文档）。

### `core/default_config/`（默认配置）

**负责**：
- ✅ 提供所有模块的「完整默认配置」
- ✅ 对配置进行**功能拆分**：`data` / `system` / `worker` / `database` / `market`
- ✅ 约定字段结构和默认值

**不负责**：
- ❌ 不负责任何加载逻辑（文件 I/O / 合并 / 校验等）
- ❌ 不负责区分环境（本地 / 线上），一切环境差异由 userspace + env 决定

---

### `userspace/config/`（用户覆盖配置）

**负责**：
- ✅ 提供用户项目级别的配置覆盖
- ✅ 只写「差异」，其余由默认配置补齐
- ✅ 作为 Git 忽略的、本地或部署环境专属配置

**不负责**：
- ❌ 不定义字段 schema（字段结构由 core/config 决定）
- ❌ 不保证配置完整性（缺失的字段由默认配置补全）

---

## 配置加载机制（概念层）

> 本节只描述「配置文件从哪来、如何被组合」的整体机制，不涉及具体类名和 API；  
> 加载实现细节由 `infra/project_context` 下的配置管理组件负责。

以数据库配置为例，整体流程如下：

```text
1. 读取默认配置
   - core/default_config/database/common.json
   - core/default_config/database/postgresql.json / mysql.json / sqlite.json

2. 读取用户配置（如果存在）
   - userspace/config/database/common.json
   - userspace/config/database/postgresql.json 等

3. 深度合并
   - 按字段进行深度合并：用户只需写需要覆盖的字段，其余继承默认配置

4. 应用环境变量覆盖
   - 例如 DB_POSTGRESQL_USER / DB_POSTGRESQL_PASSWORD 等敏感信息

5. 返回最终配置
   - 供数据库管理组件 / 连接管理器等使用
```

### 深度合并（示意）

```json
// core/default_config/data.json
{
  "default_start_date": "20080101",
  "decimal_places": 2,
  "stock_list_filter": {
    "exclude_patterns": {
      "start_with": {
        "id": ["688", "8"],
        "name": ["ST", "*ST"]
      }
    }
  }
}

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

合并结果：

```json
{
  "default_start_date": "20080101",
  "decimal_places": 2,
  "stock_list_filter": {
    "exclude_patterns": {
      "start_with": {
        "id": ["688", "8"],
        "name": ["ST", "*ST"]
      }
    }
  }
}
```

> 可以看到：用户只覆盖了 `id` 部分，其余字段保持不变。

关于「在代码中如何访问这些配置值」（例如提供按域获取完整配置、或语义化便捷方法），  
请参考 `infra/project_context` 中关于配置管理组件的架构文档。

---

## 未来扩展方向

### 待实现扩展（单机版支持）

1. **配置 Schema 校验**
   - 为每个 JSON 增加对应的 JSON Schema / Pydantic 模型
   - 在启动时进行格式和类型校验，给出友好的错误信息
2. **字段级文档化**
   - 为关键字段增加内联 `_comment` 或集中文档
   - 与 VSCode / IDE 配置提示联动（长期规划）
3. **更细粒度的环境支持**
   - 支持 `userspace/config/dev/`、`prod/` 之类的多环境目录
   - 或通过环境变量选择当前配置 profile

### 可扩展方向（超出当前单机版范围）

1. **集中式配置服务**
   - 将配置迁移到集中式配置中心（如 Consul / Etcd / Config Server）
   - 单机版不计划实现，只在需要分布式部署时考虑
2. **配置热更新**
   - 监听配置文件变化并实时生效
   - 目前仍采用「修改后重启生效」的简单模型

---

## 相关文档

- `core/default_config/README.md`：核心默认配置说明
- `core/default_config/DESIGN.md`：配置系统设计文档（本架构文档的源材料之一）
- `userspace/config/README.md`：用户配置目录说明
- [overview.md](./overview.md)：配置系统快速概览
- [decisions.md](./decisions.md)：关键设计决策记录

---

**文档结束**

