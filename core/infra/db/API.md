# Database API 文档

**版本：** `0.5.0`  
**最低支持核心版本：** `>=0.4.0`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。  
> 所列门面入口须有 `__test__/test_api.py` 覆盖。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `Db`；类型从 [`contracts.py`](./contracts.py) 导入。实现位于 [`core/`](./core/)，勿将深路径当作公开 API。

---

## Db

**描述：** 数据库门面类（Facade）— `manager` / `migration` / `engine` / `duckdb` / `sql` / `rows` 命名空间

### manager

**描述：** 运行时 `DatabaseManager` 的创建与默认实例

#### get_default

`Db.manager.get_default(*, auto_init: bool = True) -> DatabaseManager`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`
- **描述：** 获取进程内默认数据库管理器（可按需自动 initialize）
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `auto_init` (可选) | `bool` | 默认 `True` |

- **返回值：** `DatabaseManager`
- **举例：**

```python
from core.infra.db import Db

db = Db.manager.get_default()
```

#### create

`Db.manager.create(config: dict | None = None, *, is_verbose: bool = False) -> DatabaseManager`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`
- **描述：** 构造管理器实例（不自动设为 default）
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `config` (可选) | `dict \| None` | 缺省则从 ProjectContext 加载 |
| `is_verbose` (可选) | `bool` | 默认 `False` |

- **返回值：** `DatabaseManager`

#### set_default / reset_default

`Db.manager.set_default(manager) -> None`  
`Db.manager.reset_default() -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`
- **描述：** 设置 / 清除进程内默认实例

---

### migration

**描述：** Schema 迁移编排（实现：`MigrationManager`；CLI：`python -m core.infra.db.core.migrate_manager`）

#### default_snapshot_path

`Db.migration.default_snapshot_path(repo_root: Path) -> Path`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.5.0`
- **描述：** 默认 pre-mirror schema 快照路径

#### build_plan

`Db.migration.build_plan(old_schemas, new_schemas, *, database_type=..., db=...) -> ...`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`
- **描述：** 转发 `MigrationManager.build_plan`

#### run

`Db.migration.run(pre_mirror_snapshot, **kwargs) -> ...`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`
- **描述：** 转发 `MigrationManager.run`（diff → plan → apply）

#### apply

`Db.migration.apply(pre_mirror_snapshot, **kwargs) -> ...`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.5.0`
- **描述：** 执行迁移（等价 `run(..., apply=True)`）

---

### engine

**描述：** Engine 配置元信息与工厂

#### build_meta

`Db.engine.build_meta(raw_config: dict, *, is_verbose: bool = False) -> EngineConfigMeta`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.5.0`
- **描述：** 从已解析的 database 配置构造 `EngineConfigMeta`

#### create

`Db.engine.create(meta: EngineConfigMeta) -> DbEngineAbc`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.5.0`
- **描述：** 按 meta 挂载具体 Engine（未 initialize）

---

### duckdb

**描述：** DuckDB 路径、WAL 与多进程 worker 池协作

#### resolve_db_path

`Db.duckdb.resolve_db_path(db_path: str) -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.5.0`
- **描述：** 将配置中的相对/绝对 `db_path` 解析为绝对路径

#### overlay_domain_paths

`Db.duckdb.overlay_domain_paths(base_config=None, *, data=None, tag=None, strategy=None) -> dict`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.5.0`
- **描述：** 返回 database 配置副本，覆盖 DuckDB 各域 `db_path`。绝对路径可指向模块 `__performance__/.workdir/` 等非默认目录。
- **举例：**

```python
from core.infra.db import Db

cfg = Db.duckdb.overlay_domain_paths(
    data="/abs/path/perf_test_tmp.duckdb",
    tag="/abs/path/perf_test_tmp_tag.duckdb",
    strategy="/abs/path/perf_test_tmp_strategy.duckdb",
)
db = Db.manager.create(cfg)
```

#### worker_pool

**描述：** 主进程在 ProcessPool 期间释放 / 恢复 DuckDB 文件锁

| 方法 | 说明 |
|------|------|
| `is_backend(data_mgr=None)` | 当前是否 DuckDB backend |
| `should_apply(*, mode, use_process_pool, data_mgr=None)` | 是否套用 worker pool scope |
| `CONFIG_OVERLAY_ENV` | 常量 `NTQ_DATABASE_CONFIG_JSON`：spawn 配置 overlay 环境变量名 |
| `install_config_overlay(cfg)` | 将完整 database config 写入 overlay env（无 monkeypatch） |
| `prepare_main(data_mgr=None)` | 池启动前：主进程释放句柄 |
| `restore_after()` | 池结束后：恢复主进程连接 |
| `maybe_scope(data_mgr=None, **kwargs)` | 条件 context manager |
| `main_process(data_mgr=None, **kwargs)` | 强制 context manager |
| `recover_after_interrupt(data_mgr=None)` | 中断后恢复 |
| `ensure_data_manager_restored(data_mgr=None)` | 确保 DataManager 已恢复 |
| `wait_pool_children_done(*, timeout_sec=15)` | 等待子进程结束 |
| `wait_for_main_end(*, timeout_sec=600)` | 等待主进程 suspend 结束 |
| `is_main_active()` | 主进程是否处于 suspend |
| `connect_domains(db, *, domains, read_only)` | 按域连接 |
| `database_config_read_only()` | 只读域配置副本 |
| `release_worker_db_handles(data_mgr=None)` | 释放 worker 侧句柄 |
| `release_all_main_handles(data_mgr)` | 关闭主进程全部 DuckDB 连接（spawn 前） |

- **状态：** `beta`
- **引入版本：** `0.5.0`
- **举例：**

```python
from core.infra.db import Db

with Db.duckdb.worker_pool.maybe_scope(
    mode="auto", use_process_pool=True, data_mgr=data_mgr
):
    pipeline.run(jobs)
```

#### wal

**描述：** WAL / CHECKPOINT 策略查询与执行

| 方法 | 说明 |
|------|------|
| `should_checkpoint_after_batch(db_config)` | 批量写入后是否 CHECKPOINT |
| `should_checkpoint_after_persist(db_config)` | persist 后是否 CHECKPOINT |
| `should_checkpoint_on_sigint(db_config)` | SIGINT 时是否 CHECKPOINT |
| `should_checkpoint_after_tag_run(db_config)` | tag run 后是否 CHECKPOINT |
| `checkpoint_engine(engine, *, domains=None)` | 对 Engine 执行 CHECKPOINT |
| `install_sigint_checkpoint_handler(engine, db_config)` | 安装 SIGINT handler |

- **状态：** `beta`
- **引入版本：** `0.5.0`

---

### sql

**描述：** 跨后端 SQL 标识辅助

#### qualify_table_name

`Db.sql.qualify_table_name(config: dict, logical_name: str) -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.5.0`
- **描述：** 逻辑表名 → SQL 表标识（PostgreSQL 含 schema）

---

### rows

**描述：** 行数据规范化辅助

#### clean_nan_in_list

`Db.rows.clean_nan_in_list(data_list, default=None) -> list`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.5.0`
- **描述：** 清洗行字典列表中的 NaN

---

## contracts（`core.infra.db.contracts`）

**描述：** 跨模块契约类型（非门面方法；从 `contracts` 导入）

| 符号 | 说明 | 状态 |
|------|------|------|
| `DatabaseManager` | 运行时管理器类 | `beta` |
| `SchemaManager` | Schema 加载 / 校验 | `beta` |
| `DbBaseModel` | 表模型基类 | `beta` |
| `Field` | 列类型定义 | `beta` |
| `StorageRegistry`, `STORAGE_DOMAINS` | 表 → 存储域 | `beta` |
| `DbEngineAbc`, `DbTableAbc` | Engine / 表操作抽象 | `beta` |
| `EngineConfigMeta` | Engine 配置元信息 | `beta` |
| `BatchOperation`, `BatchWriteQueue` | 批量写入 | `beta` |

`DatabaseManager` 实例方法（查询 / 建表等）签名以代码与 [ARCHITECTURE.md](./docs/ARCHITECTURE.md) 为准。
