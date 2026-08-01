# Database API 文档

**版本：** `0.4.0`  
**最低支持核心版本：** `>=0.4.0`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。  
> 所列门面入口须有 `__test__/test_api.py` 覆盖。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**过渡期说明：** 存量代码大量使用 `from core.infra.db import DatabaseManager, DbBaseModel, Field`。包根与 [`contracts.py`](./contracts.py) 仍导出这些符号；新代码优先 `Db` + `contracts`。实现位于 [`core/`](./core/)。

---

## Db

**描述：** 数据库门面类（Facade）— `manager` / `migration` / `duckdb` 命名空间

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

#### build_plan

`Db.migration.build_plan(**kwargs) -> ...`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`
- **描述：** 转发 `MigrationManager.build_plan`
- **参数：** 见实现与 [DESIGN.md](./docs/DESIGN.md)

#### run

`Db.migration.run(**kwargs) -> ...`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`
- **描述：** 转发 `MigrationManager.run`（diff → plan → apply）

---

### duckdb

**描述：** DuckDB 多进程协作挂载点（过渡期）

#### process_pool_module

`Db.duckdb.process_pool_module() -> module`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`
- **描述：** 返回 `process_pool_scope` 模块，供调用方取 `prepare_main_for_worker_pool` 等函数
- **参数：** 无
- **返回值：** `module` — `core.infra.db.core.engines.duckdb.process_pool_scope`
- **举例：**

```python
from core.infra.db import Db

pps = Db.duckdb.process_pool_module()
pps.prepare_main_for_worker_pool(data_mgr)
```

---

## contracts（`core.infra.db.contracts`）

**描述：** 跨模块契约与常用类型（非门面方法，从 `contracts` 导入）

| 符号 | 说明 | 状态 |
|------|------|------|
| `DatabaseManager` | 运行时管理器类 | `beta` |
| `DbBaseModel` | 表模型基类 | `beta` |
| `Field` | 列类型定义 | `beta` |
| `StorageRegistry`, `STORAGE_DOMAINS` | 表 → 存储域 | `beta` |
| `DbEngineAbc`, `DbTableAbc` | Engine / 表操作抽象 | `beta` |
| `EngineConfigMeta`, `build_engine_meta`, `create_engine` | 配置元信息与工厂 | `beta` |
| `BatchOperation`, `BatchWriteQueue` | 批量写入 | `beta` |

`DatabaseManager` 的查询 / 建表 / DuckDB checkpoint 等方法签名以代码与 [ARCHITECTURE.md](./docs/ARCHITECTURE.md) 为准；后续版本将按方法块补全到本文件。
