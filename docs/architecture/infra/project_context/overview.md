# Project Context 模块概览

Project Context 模块属于 **Infra 层**，为整个项目提供：

- **路径管理**：统一的项目根目录、`core/`、`userspace/`、策略 / 标签 / 配置等路径
- **文件管理**：文件查找、读取、存在性检查、目录创建
- **配置管理**：默认配置 + 用户配置 的加载与合并
- **统一入口**：`ProjectContextManager` 作为 Facade 统一暴露上述能力

它的核心目标是：**让所有“我在哪”“东西放哪”“配置在哪”这类问题，都有统一、可靠、可测试的答案**。

---

## 模块角色定位

- **层级定位**：位于 `core/infra/`，和 `db`、`worker`、`discovery` 同级，是所有上层模块的基础设施
- **服务对象**：
  - `core/modules`：如 `strategy`、`data_source`、`data_manager`
  - `userspace/`：用户定义的策略、数据源、标签场景等
- **典型调用链**：
  - `strategy` 通过 Project Context 找到策略配置和结果目录
  - `data_source` 通过 Project Context 查找 `mapping.json` / 用户自定义映射
  - `data_manager` 通过 Project Context 统一访问 `config/`、`userspace/` 等目录

---

## 目录结构一览

```text
core/infra/project_context/
├── path_manager.py             # PathManager：路径管理
├── file_manager.py             # FileManager：文件管理
├── config_manager.py           # ConfigManager：配置管理
├── project_context_manager.py  # ProjectContextManager：Facade
└── DESIGN.md                   # 设计文档（实现细节）
```

在文档侧，对应的架构文档位于：

```text
docs/architecture/infra/project_context/
├── overview.md      # 当前概览文档
├── architecture.md  # 详细架构设计
└── decisions.md     # 重要决策记录
```

---

## 核心组件速览

- **PathManager**
  - 基于项目根目录提供常用路径（`core/`、`userspace/`、`config/` 等）
  - 提供策略 / 标签 / 结果等高层语义路径的构造
  - 无状态、纯函数式 API，返回 `Path` 而不产生副作用

- **FileManager**
  - 递归查找文件 / 多文件
  - 读取文件内容、检查文件 / 目录是否存在
  - 确保目录存在（必要时创建）

- **ConfigManager**
  - 支持 JSON / Python(`settings.py`) 两类配置文件
  - 提供「默认配置 + 用户配置」的合并能力
  - 复用 `deep_merge_config` 做深度合并，支持 `deep_merge_fields` / `override_fields`

- **ProjectContextManager**
  - 组合 Path / File / Config 三个 Manager
  - 提供友好的 Facade：`ctx.path.*`、`ctx.file.*`、`ctx.config.*`
  - 为上层模块隐藏具体实现细节

---

## 典型使用场景

- **策略侧**
  - 根据策略名定位：代码目录、`settings.py`、结果目录
  - 加载并合并：框架默认策略配置 + 用户策略配置

- **数据源侧**
  - 查找并合并：默认 `mapping.json` 与用户覆盖的 `mapping.json`
  - 确保日志 / 中间结果目录存在

- **通用工具侧**
  - 在 `userspace/` 下批量查找特定文件（如所有 `settings.py`）
  - 做到「只操作 Project Context 给出的路径」，避免硬编码相对路径

---

## 延伸阅读

- 详细架构设计：`architecture/infra/project_context/architecture.md`
- 重要决策记录：`architecture/infra/project_context/decisions.md`
- 相关模块：
  - `architecture/db_architecture.md`
  - `architecture/discovery_architecture.md`
  - `architecture/config_architecture.md`
