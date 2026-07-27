# Project Context（`infra.project_context`）

为全仓库提供**项目根推断**、**语义化路径**、**约定式配置发现**（`DiscoveryManager`）与 **JSON/Python 配置加载与合并**（`ConfigManager`），以及无约定布局时的**文件 I/O 原语**（`FileManager`）。

## 适用场景

- 需要解析 `userspace`、策略结果目录、数据源 handlers/providers 路径。
- 需要合并框架默认配置与用户覆盖（含数据库、Worker、日志等）。
- 需要统一 Facade：`ProjectContextManager` 暴露 `path` / `discovery` / `config` / `file`。

## 快速定位

```text
core/infra/project_context/
├── module_info.yaml
├── project_context_manager.py
├── path_manager.py
├── discovery_manager.py
├── config_manager.py
├── config_merge_policies.py
├── file_manager.py
├── __test__/
└── docs/
    ├── ARCHITECTURE.md
    ├── DESIGN.md
    ├── API.md
    └── DECISIONS.md
```

## 快速开始

```python
from core.infra.project_context import ProjectContextManager, PathManager, DiscoveryManager, ConfigManager

ctx = ProjectContextManager()
root = ctx.path.get_root()
profiles = ctx.discovery.discover_configs("markets")
data_cfg = ctx.config.load_data_config()
```

运行测试（仓库根目录）：

```bash
python3 -m pytest core/infra/project_context/__test__/ -q
```

## 模块依赖

无（YAML 级）。Worker 并发配置见 `worker.json` 的 ``job_pipeline``（由 BacktestEngine `worker_profile` 读取）。

## 当前实现说明（代码对齐）

- `PathManager.get_root()` 通过向上查找 `.git`、`pyproject.toml` 等标记定位仓库根并缓存；`core()` 优先 `core/`，兼容 `app/core/`。
- `PathManager.userspace()` 支持环境变量 `NEW_TEA_QUANT_USERSPACE_ROOT` / `NTQ_USERSPACE_ROOT`。
- `ConfigManager.load_database_config` 合并 `default_config/database/*` 与 `userspace/config/database/*`，并支持 `DB_*` 环境变量覆盖。

## 相关文档

- `docs/ARCHITECTURE.md`
- `docs/DESIGN.md`
- `docs/API.md`
- `docs/DECISIONS.md`
