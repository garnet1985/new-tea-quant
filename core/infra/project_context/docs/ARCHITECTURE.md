# Project Context 架构文档

**版本：** `0.3.0`

---

## 模块介绍

`infra.project_context` 提供 NTQ 的「我在哪、有哪些配置、配置怎么读与合并」的统一答案：项目根与语义目录、约定式配置发现、JSON/Python 加载及默认与用户合并。

---

## 模块目标

- 单一来源推断项目根与 `core` / `userspace` 等关键目录。
- 为策略、标签、数据源、Data Contract 等提供稳定路径构造，避免业务层硬编码相对路径。
- 统一默认配置（`core/default_config`）与用户配置（`userspace/config`）的发现与合并语义。
- 通过 Facade 可选地一次获取 `path` / `discovery` / `config` / `file` 能力。

---

## 模块职责与边界

**职责（In scope）**

- 根目录检测与缓存；`userspace` 环境变量覆盖。
- 基于 `pathlib.Path` 的路径 API。
- 约定式配置发现（domain + config id）、可覆盖加载、树形 `find_in_tree`。
- 配置：JSON/Python 加载、`load_with_defaults`、数据库/数据/Worker 等专项加载器。

**边界（Out of scope）**

- 不实现业务领域逻辑（策略、数据源规则等）。
- 不负责数据库连接或 Worker 进程生命周期（仅提供配置读取与路径）。
- 不替代 `logging` 模块配置应用侧初始化。

---

## 依赖说明

- 无 `module_info.yaml` 声明的模块依赖；标准库为主。`ProjectContextManager.core_info` 可选读取 `core.system`；`get_module_config` 在调用链内引用 `infra.worker` 的类型。

---

## 工作拆分

- `PathManager`（`path_manager.py`）：`get_root` 与缓存；`core`/`userspace`/策略/标签/数据源/Data Contract 等语义路径。
- `DiscoveryManager`（`discovery_manager.py`）：`discover_configs`、`discover_config`、`load_overridable_config`、`find_in_tree`。
- `ConfigManager`（`config_manager.py`）：`load_with_defaults`、`load_json`/`load_python`、数据库与各类 `load_*_config`、环境变量覆盖、便捷 getter。
- `FileManager`（`file_manager.py`）：`find_file`/`find_files`、`read_file`、存在性、`ensure_dir`（无约定布局的 I/O 原语）。
- `ProjectContextManager`（`project_context_manager.py`）：挂载各 Manager；`core_info`/`core_version`。

---

## 架构/流程图

```text
ProjectContextManager
├── PathManager（静态）
├── DiscoveryManager（静态）
├── ConfigManager（静态）
└── FileManager（静态）
```

```text
配置: default_config[/domain]/{id}.json + userspace/config[/domain]/{id}.json
      -> DiscoveryManager.load_overridable_config -> Dict
数据库: database/common + database/{type} + env 覆盖
```

---

## 相关文档

- [详细设计](./DESIGN.md)
- [API](./API.md)、[决策记录](./DECISIONS.md)
