# Project Context 架构文档

**版本：** `0.4.0`

---

## 模块介绍

`infra.project_context` 提供 NTQ 的「我在哪、有哪些配置、配置怎么读与合并」的统一答案：项目根与语义目录、约定式配置发现、JSON/Python 加载及默认与用户合并。

**核心设计：** 采用 **Facade + Abstract Interface** 模式，对外只暴露 `ProjectContextManager` 作为唯一入口，防止误用，确保API契约稳定。

---

## 模块目标

- **单一入口点：** 用户只通过 `ProjectContextManager` 访问功能，不直接使用内部Manager。
- **API契约明确：** `ProjectContextAPI` 抽象类定义所有对外API（16个核心API）。
- **防止误用：** `PathManager`、`ConfigManager`、`FileManager`、`DiscoveryManager` 变成内部实现，不对外暴露。
- 提供稳定路径构造，避免业务层硬编码相对路径。
- 统一默认配置（`core/default_config`）与用户配置（`userspace/config`）的发现与合并语义。

---

## 模块职责与边界

**职责（In scope）**

- **对外唯一入口：** `ProjectContextManager` 提供所有API。
- **API契约定义：** `ProjectContextAPI` 抽象类定义所有对外API。
- **内部实现私有：** 内部Manager（PathManager等）不对外暴露。
- 根目录检测与缓存；`userspace` 环境变量覆盖。
- 基于 `pathlib.Path` 的路径 API（统一命名规范）。
- 约定式配置发现、可覆盖加载、树形 `find_in_tree`。
- 配置：JSON/Python 加载、`load_with_defaults`、数据库/数据/Worker 等专项加载器。

**边界（Out of scope）**

- 不实现业务领域逻辑（策略、数据源规则等）。
- 不负责数据库连接或 Worker 进程生命周期（仅提供配置读取与路径）。
- 不替代 `logging` 模块配置应用侧初始化。

---

## 依赖说明

- 无外部模块依赖；标准库为主。
- `ProjectContextManager.core_info` 可选读取 `core.system`。

---

## 架构设计

### **Facade + Abstract Interface 模式**

```text
对外暴露：
  ProjectContextAPI (抽象类/接口)
    ↓
  ProjectContextManager (实现类，对外唯一入口)

内部实现：
  PathManager (内部类，不对外暴露)
  FileManager (内部类，不对外暴露)
  ConfigManager (内部类，不对外暴露)
  DiscoveryManager (内部类，不对外暴露)
```

### **API分组**

| 分组 | API数量 | 说明 |
|------|---------|------|
| 路径核心 | 5个 | `get_project_root`, `get_core_root`, `get_userspace_root`, `get_strategy_directory`, `get_tag_directory` |
| 配置核心 | 3个 | `load_core_config`, `load_database_config`, `load_data_config` |
| 发现核心 | 3个 | `discover_strategies`, `discover_tags`, `discover_configs` |
| 文件核心 | 2个 | `find_file`, `load_file_content` |
| 元数据核心 | 2个 | `core_version`, `core_info` |
| 缓存管理 | 1个 | `clear_userspace_cache` |
| **总计** | **16个** | 所有API都是实例方法 |

---

## 使用方式

**唯一入口（推荐）：**

```python
from core.infra.project_context import ProjectContextManager

ctx = ProjectContextManager()
root = ctx.get_project_root()
core_dir = ctx.get_core_root()
settings = ctx.load_core_config("logging")
strategies = ctx.discover_strategies()
```

**禁止的方式（已不对外暴露）：**

```python
# ❌ 旧方式（已删除）
from core.infra.project_context import PathManager, ConfigManager

root = PathManager.get_project_root()  # 不推荐，不对外暴露
```

---

## 架构优势

| 维度 | 优势 |
|------|------|
| **单一入口点** | ✅ 用户只通过 ProjectContextManager 访问功能，不会混乱 |
| **API契约明确** | ✅ 抽象类定义所有对外API，契约稳定 |
| **防止误用** | ✅ 内部Manager不暴露，用户不会错误调用 |
| **易于维护** | ✅ 修改API只影响抽象类和实现类 |
| **易于测试** | ✅ 针对抽象接口写API测试 |
| **职责清晰** | ✅ Facade模式，职责明确 |

---

## 配置发现流程

```text
配置: default_config[/domain]/{id}.json + userspace/config[/domain]/{id}.json
      -> DiscoveryManager.load_overridable_config -> Dict
数据库: database/common + database/{type} + env 覆盖
```

---

## 相关文档

- [详细设计](./DESIGN.md)
- [决策记录](./DECISIONS.md)
- [API契约](../api.yaml) - api.yaml定义所有API契约
- [API测试](../__test__/test_api.py) - test_api.py测试所有API契约