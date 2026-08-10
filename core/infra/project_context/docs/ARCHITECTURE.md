# Project Context 架构文档

**版本：** `0.2.0`

---

## 模块介绍

`infra.project_context` 提供 NTQ 的「我在哪、有哪些配置、配置怎么读与合并」的统一答案：项目根与语义目录、约定式配置发现、默认与用户配置合并。

**核心设计：** Facade 模式。包根只导出 `ProjectContext`；类型与常量走 `contracts` 或 `ProjectContext.types`；`PathManager` / `ConfigManager` / `DiscoveryManager` 为内部实现。

---

## 模块目标

- 单一入口：`ProjectContext` + namespace（`path` / `config` / `meta` / `cache` / `discovery` / `types`）
- 稳定路径构造，避免业务硬编码相对路径
- 统一 `core/default_config` 与 `userspace/config` 的发现与合并语义

---

## 模块职责与边界

**职责（In scope）**

- 根目录检测与缓存；userspace 环境变量与 `.ntq/userspace-path.json` 覆盖
- 基于 `pathlib.Path` 的语义路径 API（含 `coerce_strategy_folder`、`get_backup_data_directory`）
- 约定式配置发现与可覆盖加载
- JSON 配置加载与合并（含 database / data 专项）

**边界（Out of scope）**

- 业务领域逻辑（策略、数据源规则等）
- 数据库连接或 Worker 进程生命周期
- 通用文件发现 IO（见 `infra.discovery`，含 `find_in_tree`）

---

## 依赖说明

- 无 YAML 级外部模块依赖；标准库为主
- `ProjectContext.meta.core_info` 可选读取 `core.system`

---

## 架构设计

```text
对外：
  ProjectContext
    ├── path / config / meta / cache / discovery / types
    └── contracts（异常、常量、合并函数）

内部（core/）：
  PathManager · ConfigManager · DiscoveryManager
```

配置发现：

```text
default_config[/domain]/{id}.json + userspace/config[/domain]/{id}.json
  -> discovery.load_overridable_config -> Dict
database: common + {type} + env 覆盖
```

userspace 解析：

```text
NEW_TEA_QUANT_USERSPACE_ROOT
  -> NTQ_USERSPACE_ROOT
  -> {project_root}/.ntq/userspace-path.json
  -> {project_root}/userspace
```

---

## 使用方式

```python
from core.infra.project_context import ProjectContext

root = ProjectContext.path.get_project_root()
folder = ProjectContext.path.coerce_strategy_folder("demo/my_strategy")
backup_data = ProjectContext.path.get_backup_data_directory()
settings = ProjectContext.config.load_core_config("logging")
ids = ProjectContext.discovery.discover_configs("markets")
```

禁止直接依赖内部 Manager：

```python
# ❌
from core.infra.project_context.core.path_manager import PathManager
```

类型与常量：

```python
from core.infra.project_context import ProjectContext

err = ProjectContext.types.OverridableConfigNotFoundError
```

---

## 相关文档

- [详细设计](./DESIGN.md)
- [API](../API.md)
- [契约测试](../__test__/test_api.py)
