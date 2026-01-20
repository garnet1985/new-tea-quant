# Project Context 架构文档

**版本：** 1.0  
**日期：** 2026-01-XX  
**状态：** 生产环境使用中

---

## 📋 目录

1. [设计背景](#设计背景)
2. [核心设计思想](#核心设计思想)
3. [架构设计](#架构设计)
4. [核心组件与职责](#核心组件与职责)
5. [运行时 Workflow](#运行时-workflow)
6. [典型使用场景](#典型使用场景)
7. [重要决策记录 (Decisions)](#重要决策记录-decisions)
8. [版本历史](#版本历史)

---

## 设计背景

### 问题背景

在引入 Project Context 模块之前，项目中存在如下问题：

1. **路径到处硬编码**
   - 大量类似 `"../userspace/strategies"`、`"core/modules/strategy"` 的字符串常量散落在各个模块
   - 一旦目录结构调整，容易出现「半数代码没改到」的问题

2. **项目根目录不统一**
   - 不同模块各自用 `__file__`、`os.getcwd()` 等方式推断根目录
   - 在测试 / 脚本 / IDE 运行模式下，行为不一致，容易出现「在我机子上可以」的问题

3. **配置加载逻辑重复**
   - `strategy`、`data_source`、`userspace` 等模块都有自己的「默认配置 + 用户配置」合并逻辑
   - JSON / Python 配置的读取与合并代码高度重复，维护成本高

4. **文件操作分散**
   - 文件查找、读取、目录创建逻辑杂糅在业务代码里
   - 测试和重构成本高，不利于复用

### 设计目标

1. **统一项目上下文**：提供统一的「项目根」「核心目录」「用户空间」等语义
2. **消除路径硬编码**：所有路径都经由 Project Context 获取
3. **复用配置逻辑**：将「默认配置 + 用户配置」合并逻辑集中到一个模块
4. **提高可测试性**：路径 / 文件 / 配置操作都可以单独单元测试
5. **保持无状态与轻量**：不引入复杂生命周期，尽量使用无状态工具 + 轻量 Facade

---

## 核心设计思想

### 1. 「上下文」抽象，而非某个具体服务

Project Context 不做业务逻辑，而是回答三个问题：

1. **我在哪？**（项目根目录 / 当前运行环境）
2. **东西放哪？**（策略 / 标签 / 结果 / 配置等的标准路径）
3. **配置怎么生效？**（默认配置 + 用户配置 的合并策略）

因此设计上偏向于：

- 统一的路径约定
- 统一的文件操作工具
- 统一的配置加载与合并行为

### 2. 无状态工具 + 轻量 Facade

- `PathManager` / `FileManager` / `ConfigManager` 均为 **无状态工具类**：
  - 使用 `@staticmethod` + `Path` / `dict` 输入输出
  - 不持有运行时状态，可安全复用与单元测试
- `ProjectContextManager` 只是一个组合这些工具的 Façade：
  - 不负责缓存复杂状态
  - 主要提供友好的 API 命名与入口聚合

### 3. 约定优于配置

- 项目根目录检测基于一组「约定标记」（如 `.git`、`pyproject.toml`、`README.md`）
- 目录结构有固定约定：
  - `core/`：框架核心
  - `userspace/`：用户代码
  - `config/`：全局配置
  - `userspace/strategies/<name>/settings.py`：策略配置
- 大部分场景只需遵循目录命名约定，而无需额外配置

### 4. 配置合并策略清晰可控

- 通过 `deep_merge_config` 支持深度合并
- 显式声明哪些字段「深度合并」(`deep_merge_fields`)，哪些字段「完全覆盖」(`override_fields`)
- 同时支持 JSON 与 Python 配置文件：
  - JSON：适合框架内置默认配置
  - Python：适合用户灵活自定义

---

## 架构设计

### 模块结构

```text
core/infra/project_context/
├── path_manager.py             # PathManager：路径管理
├── file_manager.py             # FileManager：文件管理
├── config_manager.py           # ConfigManager：配置管理
├── project_context_manager.py  # ProjectContextManager：统一入口（Facade）
└── DESIGN.md                   # 设计文档（实现细节）
```

### 分层视角

```text
       上层模块（core/modules, userspace/...）
                    │
                    ▼
        ProjectContextManager（统一入口 / Facade）
           ┌─────────┼─────────┐
           ▼         ▼         ▼
    PathManager  FileManager  ConfigManager
       (路径)       (文件)        (配置)
```

- 上层模块 **优先通过 `ProjectContextManager`** 使用能力
- 如需更细粒度控制，也可以直接引入对应的 Manager

---

## 核心组件与职责

### 1. PathManager（路径管理器）

**职责：**

- 检测并缓存项目根目录
- 提供标准目录路径：
  - `core/`、`userspace/`、`config/` 等
- 提供语义化路径构造：
  - 策略目录、策略配置、策略结果目录
  - 标签场景目录等

**典型 API：**

```python
from app.core.infra.project_context import PathManager

root = PathManager.get_root()
core_dir = PathManager.core()
userspace_dir = PathManager.userspace()
config_dir = PathManager.config()

strategy_dir = PathManager.strategy("example")
strategy_settings = PathManager.strategy_settings("example")
strategy_results = PathManager.strategy_results("example")
tag_scenario_dir = PathManager.tag_scenario("momentum")
```

**设计要点：**

- 返回值均为 `pathlib.Path` 对象
- 不主动创建目录（是否创建由调用方或 `FileManager` 决定）
- 项目根目录计算完成后会缓存，避免重复遍历

---

### 2. FileManager（文件管理器）

**职责：**

- 基于 `Path` 提供常用文件 / 目录操作：
  - 单文件查找、批量查找
  - 文件读取
  - 文件 / 目录存在性检查
  - 确保目录存在

**典型 API：**

```python
from app.core.infra.project_context import FileManager

settings_file = FileManager.find_file("settings.py", base_dir, recursive=True)
all_settings = FileManager.find_files("settings.py", base_dir, recursive=True)

content = FileManager.read_file(settings_file, encoding="utf-8")

FileManager.file_exists(settings_file)
FileManager.dir_exists(base_dir)
FileManager.ensure_dir(PathManager.strategy_results("example"))
```

**设计要点：**

- 全面使用 `pathlib.Path`
- 尽量不抛异常，以下场景走「温和失败」：
  - 未找到文件：返回 `None` / `[]`
  - 目录不存在：`dir_exists` 返回 `False`
- 将「目录创建」集中在 `ensure_dir`，避免在业务代码中散落 `mkdir(parents=True, exist_ok=True)`

---

### 3. ConfigManager（配置管理器）

**职责：**

- 加载 JSON / Python 配置文件
- 合并默认配置与用户配置
- 提供一致的配置读取入口

**核心 API：**

```python
from app.core.infra.project_context import ConfigManager

# 单文件加载
config = ConfigManager.load_json(path)
py_config = ConfigManager.load_python(path, var_name="settings")

# 默认配置 + 用户配置 合并
settings = ConfigManager.load_with_defaults(
    default_path=default_settings_path,
    user_path=user_settings_path,
    deep_merge_fields={"params"},      # 深度合并的字段
    override_fields={"dependencies"},  # 完全覆盖的字段
    file_type="py",                    # "json" | "py"
)
```

**合并规则：**

- 对于出现在 `deep_merge_fields` 中的 key：
  - 使用 `deep_merge_config` 做递归合并（适合嵌套 dict）
- 对于出现在 `override_fields` 中的 key：
  - 用户配置完全覆盖默认配置
- 其他字段：
  - 默认采用「浅合并」策略：用户配置优先，默认配置兜底

**设计要点：**

- 保证「**默认配置始终存在**」，即使用户不提供配置文件
- 在加载 Python 配置时，使用 `importlib` 动态导入，并从模块中提取指定变量（如 `settings`）
- 明确错误边界：找不到用户配置文件时，按「只有默认配置」处理，而非报错

---

### 4. ProjectContextManager（项目上下文管理器 / Facade）

**职责：**

- 为上层模块提供一个统一入口：
  - `ctx.path`：PathManager
  - `ctx.file`：FileManager
  - `ctx.config`：ConfigManager
- 将路径 / 文件 / 配置三类职责组织在一起，便于发现和使用

**使用示例：**

```python
from app.core.infra.project_context import ProjectContextManager

ctx = ProjectContextManager()

# 路径
core_dir = ctx.path.core()
strategy_dir = ctx.path.strategy("example")

# 文件
settings_files = ctx.file.find_files("settings.py", ctx.path.userspace(), recursive=True)

# 配置
default_settings = ctx.path.core() / "modules" / "strategy" / "default_settings.json"
user_settings = ctx.path.strategy_settings("example")
settings = ctx.config.load_with_defaults(
    default_settings,
    user_settings,
    deep_merge_fields={"params"},
    file_type="py",
)
```

**设计要点：**

- 自身保持极薄，不增加新的复杂状态
- 构造成本极低，可在需要时自由创建
- 是否需要强单例由后续实践决定，当前实现以「轻量实例 + 内部静态工具」为主

---

## 运行时 Workflow

### 场景 1：策略运行时加载配置

```text
1. 策略框架拿到策略名（如 "momentum"）
2. 通过 ProjectContextManager 获取策略配置路径：
   - default: core/modules/strategy/default_settings.json
   - user: userspace/strategies/momentum/settings.py
3. 调用 ConfigManager.load_with_defaults 合并配置
4. 将合并后的 settings 传入策略执行逻辑
```

伪代码：

```python
ctx = ProjectContextManager()

default_settings = ctx.path.core() / "modules" / "strategy" / "default_settings.json"
user_settings = ctx.path.strategy_settings("momentum")

settings = ctx.config.load_with_defaults(
    default_settings,
    user_settings,
    deep_merge_fields={"params"},
    file_type="py",
)
```

### 场景 2：DataSource 加载 mapping 配置

```text
1. DataSource 模块希望加载 handlers/mapping.json
2. 通过 PathManager 拿到：
   - 默认 mapping: core/modules/data_source/handlers/mapping.json
   - 用户 mapping: userspace/data_source/mapping.json（可选）
3. 通过 ConfigManager.load_with_defaults 合并
4. 将合并后的 mapping 传入 DataSourceManager
```

### 场景 3：批量发现策略配置文件

```python
ctx = ProjectContextManager()

strategies_dir = ctx.path.userspace() / "strategies"
settings_files = ctx.file.find_files("settings.py", strategies_dir, recursive=True)

for path in settings_files:
    # 根据路径反推出策略名，并加载配置
    ...
```

---

## 典型使用场景

1. **策略配置管理**
   - 统一从默认配置 + 用户配置构造最终策略配置
   - 防止每个策略都实现一套独立的配置加载逻辑

2. **数据源配置管理**
   - 合并默认 mapping 与用户 mapping
   - 保证 DataSource 框架与用户自定义部分可以共存

3. **统一结果目录管理**
   - 所有策略结果均写入 `PathManager.strategy_results(name)` 给出的目录
   - FileManager 负责确保目录存在

4. **工具脚本 / CLI**
   - 任何脚本都可以通过 Project Context 获取正确的项目根，而不依赖当前工作目录

---

## 重要决策记录 (Decisions)

重要决策的详细说明见：`architecture/infra/project_context/decisions.md`。

本架构文档只做简要索引：

1. 使用 `pathlib.Path` + 无状态工具类
2. 项目根目录的发现规则与缓存策略
3. 支持 JSON + Python 两类配置文件，并明确合并规则
4. 提供 ProjectContextManager 作为 Facade，而不是让各模块直接耦合多个 Manager

---

## 版本历史

### 版本 1.0 (2026-01-XX)

**主要内容：**

- 整理 Project Context 模块的职责边界
- 提炼 PathManager / FileManager / ConfigManager / ProjectContextManager 四个组件
- 引入统一的配置合并接口 `load_with_defaults`
- 补充单元测试保障路径 / 文件 / 配置行为一致
