# Project Context（`infra.project_context`）

为全仓库提供**项目根推断**、**语义化路径**（策略、标签、数据源、Data Contract 等）、**文件查找与读写**，以及 **JSON/Python 配置加载与合并**（含 `core/default_config` 与 `userspace/config`）。

## 适用场景

- 需要解析 `userspace`、策略结果目录、数据源 handlers/providers 路径。
- 需要合并框架默认配置与用户覆盖（含数据库、Worker、日志等）。
- 需要统一 Facade：`ProjectContextManager` 暴露 `path` / `file` / `config` 三个无状态 Manager。

## 快速定位

```text
core/infra/project_context/
├── module_info.yaml
├── project_context_manager.py
├── path_manager.py
├── file_manager.py
├── config_manager.py
├── __test__/
└── docs/
    ├── ARCHITECTURE.md
    ├── DESIGN.md
    ├── API.md
    └── DECISIONS.md
```

## 快速开始

```python
from core.infra.project_context import ProjectContextManager, PathManager, ConfigManager

ctx = ProjectContextManager()
root = ctx.path.get_root()
data_cfg = ctx.config.load_data_config()
```

运行测试（仓库根目录）：

```bash
python3 -m pytest core/infra/project_context/__test__/ -q
```

## 模块依赖

无（YAML 级）。`ConfigManager.get_module_config` 在调用时按需导入 `infra.worker` 的 `TaskType`，不在模块 import 时依赖 Worker。

## 当前实现说明（代码对齐）

- `PathManager.get_root()` 通过向上查找 `.git`、`pyproject.toml` 等标记定位仓库根并缓存；`core()` 优先 `core/`，兼容 `app/core/`。
- `PathManager.userspace()` 支持环境变量 `NEW_TEA_QUANT_USERSPACE_ROOT` / `NTQ_USERSPACE_ROOT`。
- `ConfigManager.load_database_config` 合并 `default_config/database/*` 与 `userspace/config/database/*`，并支持 `DB_*` 环境变量覆盖。

## 相关文档

- `docs/ARCHITECTURE.md`
- `docs/DESIGN.md`
- `docs/API.md`
- `docs/DECISIONS.md`
