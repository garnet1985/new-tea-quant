# Database 模块（`infra.db`）

数据库基础设施层，负责 NTQ 在 PostgreSQL/MySQL 上的统一连接、schema 与表写入能力。

## 适用场景

- 上层模块需要统一执行 SQL 查询。
- 需要批量写入与异步写入队列能力。
- 需要根据 schema 自动建表和表结构管理。
- 需要在多进程场景中使用默认数据库实例。

## 快速定位

```text
core/infra/db/
├── module_info.yaml
├── db_manager.py
├── connection_management/
├── schema_management/
├── table_management/
├── table_queriers/
├── helpers/
└── docs/
    ├── ARCHITECTURE.md
    ├── DESIGN.md
    ├── API.md
    └── DECISIONS.md
```

升级用 **单步数据脚本** 放在同级包 **`core/infra/update/db/`**（由本模块注册表引用，见下文「与 updater / 数据脚本的边界」）。

## 模块依赖

- `infra.project_context`：用于读取数据库配置与项目路径上下文。

## 当前实现说明（代码对齐）

- 当前支持数据库类型：`postgresql`、`mysql`。
- 不包含 SQLite 适配器与配置解析支持。
- 默认实例通过 `DatabaseManager.set_default/get_default` 管理。

## Schema 与升级（约定，实施中）

本模块负责 **数据库结构** 与 **升级时的 schema 迁移**；**应用升级编排**在 `userspace/updater/`（见该目录 `README.md` §8 / §8.1）。

### `update_key`（`core/tables`）

- 每个 **`core/tables/**/schema.py`** 内的 `schema` dict 须含 **`update_key`**：作者手填、**全局唯一**的稳定字符串，用于迁移脚本、`action_id` 与 diff 锚定；**不等同于**物理表名 `name`（表名可改，`update_key` 不轻易改）。  
- 加载时由 **`SchemaManager._validate_schema`** 校验；`load_all_schemas` 检查 **重复 `update_key`**。  
- **`userspace`** 等非 `core/tables` 路径下的 schema **不要求** `update_key`。

### 迁移管线（概念分层）

1. **Diff report**：仅描述相对「当前库 introspection」与「期望 schema（代码）」的差异；三维度：**meta**（如表重命名，自动化路径中 **最后执行**）、**fields**、**indexes**。  
   **升级场景**：「升级前期望」应来自 updater 在 **`managed_scope` 镜像之前** 写入的 **`userspace/.ntq/update/cache/pre_mirror_core_table_schemas.json`**（`{表名: schema dict}`），勿依赖镜像后仍可从旧路径读取的 `core/tables`；「升级后期望」来自镜像后的代码或 staging 中的新版 `core/tables`。  
2. **Execution plan**：由 diff 编译出的可执行单元，带 **`depends_on` / `action_id`**；**拓扑排序**后执行。  
3. **索引（简化策略）**：若某表存在 **字段类变更**，则对该表先 **删除全部二级索引**，字段 DDL 完成后再按期望 schema **重建索引**；仅索引变化且无字段变更时，可对索引做增量 DROP/CREATE。  
4. **新列**：默认 **`NULL`**；若存在与 `action_id` 对应的 **数据脚本** 则执行（脚本/registry 路径在实现时定）；无脚本则保持全空。破坏性变更（改类型、缩 `varchar`、删列等）走 **显式脚本或拒绝自动**。  
5. **执行入口**：由本包提供 **单一 CLI/模块入口**（如 `python -m core.infra.db.migrate`），由 updater **子进程**调用；**编排**（何时 spawn、传参、成败是否阻断升级）在 updater，**diff → plan → 执行 plan（DDL + 调度数据脚本）** 在本包内完成。子命令/阶段（如 `plan` / `apply` 或单进程内连续阶段）在首次落地代码时与此处对齐。

### 与 updater / 数据脚本的边界

| 责任方 | 内容 |
|--------|------|
| **`core/infra/db`** | **schema diff**、**diff → execution plan**、**实施 plan**（DDL、方言、拓扑执行）、**幂等与迁移历史表**、按注册表 **调用** 数据脚本 |
| **`core/infra/update/db`**（与 `core/infra/db` 并列的包） | **升级用单步脚本**（回填、破坏性变更等）：由 **`update_key` / `action_id`** 注册；**不负责** diff/plan/编排；由 **`core/infra/db`** 在执行 plan 时解析注册表并调用 |
| **`userspace/updater`** | 流水线编排：镜像前 **schema 快照**（见该目录 `README.md` §8 步骤 6）；`_run_database_migrations` 内 **spawn**、环境变量、`PYTHONPATH=repo_root`；不实现 SQL、不扫描脚本目录 |

### 职责与接口契约（已定）

- **Plan 产物**：以 **进程内数据结构**（变量 / 对象）为主即可；若需 dry-run、排障或重放，可 **额外** 落盘到 `userspace/.ntq/update/cache/`（非必选）。  
- **编排 vs 执行**：updater 与子进程之间约定 **少量 CLI 子命令与退出码**；子进程内由 **`core/infra/db`** 完成 plan 与执行，避免 updater `import` 长事务迁移逻辑。  
- **脚本如何被找到**：在 **`core/infra/db`** 内维护 **`update_key` / `action_id` → 可调用项或脚本路径** 的注册表；**`core/infra/update/db`** 只放实现，由注册表挂接。  
- **数据脚本 vs DDL**：DDL 与脚本 **调度** 均在 **`core/infra/db`**；脚本 **实现** 在 **`core/infra/update/db`**；失败记录与幂等仍以 **`core/infra/db`** 为准，updater 仅看进程退出码。  
- **升级时 diff 的「旧 / 新」期望**：**旧版** = 镜像前快照 **`pre_mirror_core_table_schemas.json`**；**新版** = 镜像后的 **`core/tables`**（在 staging 未清理前也可与 staging 内新版对齐，语义一致）。即 **新版 tables schema 与旧版（快照）对比**，再结合当前库 introspection。

## 相关文档

- `docs/ARCHITECTURE.md`
- `docs/DESIGN.md`
- `docs/API.md`
- `docs/DECISIONS.md`
