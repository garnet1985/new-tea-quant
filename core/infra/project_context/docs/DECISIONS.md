# Project Context 决策记录

**模块版本：** `0.4.0`

---

## 决策 1：Facade + Abstract Interface 单一入口点

1. **背景（Context）**
   之前的架构允许多入口点，用户可以直接使用 `PathManager`、`ConfigManager`、`FileManager`、`DiscoveryManager`，导致API重复、命名混乱、容易误用。

2. **决策（Decision）**
   采用 **Facade + Abstract Interface** 模式：
   - 创建 `ProjectContextAPI` 抽象类，定义所有对外API（16个核心API）。
   - `ProjectContextManager` 实现抽象类，作为对外唯一入口。
   - `PathManager`、`ConfigManager`、`FileManager`、`DiscoveryManager` 变成内部实现，不对外暴露。

3. **理由（Rationale）**
   - 单一入口点，防止用户误用。
   - API契约明确，抽象类定义所有API，契约稳定。
   - 易于维护，修改API只影响抽象类和实现类。
   - 易于测试，针对抽象接口写API测试。

4. **影响（Consequences）**
   - 用户只能通过 `ProjectContextManager` 访问功能。
   - 内部Manager不暴露，防止错误调用。
   - 45个调用方文件需要更新导入方式。

5. **备选方案（Alternatives）**
   - 保留多入口点（导致API混乱、容易误用）。

---

## 决策 2：对外统一使用实例方法

1. **背景（Context）**
   Python 的 `abc.ABC` 和 `@abstractmethod` 不支持静态方法，需要选择实例方法或类方法。

2. **决策（Decision）**
   所有对外API都使用实例方法：
   - `ProjectContextAPI` 定义实例方法（使用 `@abstractmethod`）。
   - `ProjectContextManager` 实现实例方法。
   - 用户需要先创建实例：`ctx = ProjectContextManager()`，然后调用：`ctx.get_project_root()`。

3. **理由（Rationale）**
   - 符合Python惯例（ABC 抽象类通常用实例方法）。
   - 简单清晰，只有一种调用方式，不会混淆。
   - 内部实现不受影响（内部Manager仍然用静态方法）。
   - 易于测试（针对实例写API测试）。

4. **影响（Consequences）**
   - 用户需要先创建实例，不能静态调用。
   - 调用方式变为 `ctx.get_project_root()` 而非 `ProjectContextManager.get_project_root()`。

5. **备选方案（Alternatives）**
   - 使用 `typing.Protocol`（仅类型提示，不是运行时强制）。
   - 混合方案（既支持实例方法，也支持类静态方法）。

---

## 决策 3：对外统一使用 `pathlib.Path`

1. **背景（Context）**
   字符串路径与 `os.path` 混用易导致拼接错误与平台差异。

2. **决策（Decision）**
   对外 API 以 `Path` 表示路径；仅在必要时对第三方接口转为 `str`。

3. **理由（Rationale）**
   类型一致、可读、跨平台语义由标准库处理。

4. **影响（Consequences）**
   调用方需习惯 `Path` 运算。

5. **备选方案（Alternatives）**
   全 `str`（易错）；自定义路径类型（过重）。

---

## 决策 4：项目根目录统一发现与缓存

1. **背景（Context）**
   各模块自行推断根目录时，在测试、脚本、IDE 下行为不一致。

2. **决策（Decision）**
   `PathManager.get_project_root()` 自包路径向上查找根标记（`.git`、`pyproject.toml` 等），命中后写入 `_root_cache`。

3. **理由（Rationale）**
   行为一致；首次遍历后 O(1)。

4. **影响（Consequences）**
   极罕见布局若无标记则走 fallback 父链。

5. **备选方案（Alternatives）**
   仅 `os.getcwd()`（不可靠）。

---

## 决策 5：配置格式与合并集中在 `ConfigManager`

1. **背景（Context）**
   JSON 与 Python 配置、默认与用户合并逻辑曾分散实现。

2. **决策（Decision）**
   支持 JSON 与 Python（`importlib` 加载）；`load_with_defaults` + `deep_merge_config` 处理 `deep_merge_fields` / `override_fields`；`load_core_config` 约定 `default_config` + `user_config` 文件名。

3. **理由（Rationale）**
   合并语义一处维护；业务按名选用加载器。

4. **影响（Consequences）**
   复杂合并规则继续在 `ConfigManager` 演进。

5. **备选方案（Alternatives）**
   各业务自写合并（重复与不一致）。

---

## 决策 6：温和失败（缺文件不抛）

1. **背景（Context）**
   可选文件未创建时不应阻断探索性流程。

2. **决策（Decision）**
   `find_file` 返回 `None`，`find_files` 返回 `[]`，读失败返回 `None`；用户配置缺失时 `load_with_defaults` 退回默认；`load_core_config` 配置不存在时返回空字典。

3. **理由（Rationale）**
   Infra 提供原子能力；「是否必填」由上层定义。

4. **影响（Consequences）**
   调用方需处理空值。

5. **备选方案（Alternatives）**
   一律抛错（对脚手架不友好）。

---

## 决策 7：API命名规范统一

1. **背景（Context）**
   之前的命名不规范，有的缺少 `get_` 前缀，有的命名不清晰（如 `invalidate_userspace_cache`），有的命名不一致（有的有 `_root` 后缀，有的没有）。

2. **决策（Decision）**
   统一命名规范：
   - **路径获取：**
     - 根目录：`get_xxx_root()`（如 `get_project_root()`, `get_core_root()`）
     - 目录：`get_xxx_directory()`（如 `get_strategy_directory()`）
     - 文件路径：`get_xxx_path()`（暂未对外暴露）
   - **缓存清理：** `clear_xxx_cache()`（而非 `invalidate_xxx_cache`）
   - **配置加载：** `load_xxx_config()`（如 `load_core_config()`）

3. **理由（Rationale）**
   命名清晰、一致，符合CODE_STYLE.md规范。

4. **影响（Consequences）**
   所有旧方法名都删除（不做向后兼容），45个调用方文件需要更新。

5. **备选方案（Alternatives）**
   保留旧方法名做向后兼容（导致命名混乱）。

---

## 决策 8：API契约文档化（api.yaml + test_api.py）

1. **背景（Context）**
   之前缺少API契约文档，开发者和测试不知道有哪些对外API、怎么用、参数和返回值是什么。

2. **决策（Decision）**
   创建API契约文档体系：
   - **api.yaml：** 定义所有API契约（描述、参数、返回值、异常、示例）。
   - **api.py：** 定义抽象接口（所有16个核心API）。
   - **test_api.py：** 测试所有API契约（46个测试，确保三者一致）。

3. **理由（Rationale）**
   - 开发者和测试可以快速查阅API。
   - API契约稳定，防止随意修改。
   - 测试覆盖所有API，确保契约正确。

4. **影响（Consequences）**
   - 需要维护三者一致性（api.py、api.yaml、test_api.py）。
   - 新增API时需要同步更新三者。

5. **备选方案（Alternatives）**
   - 仅使用代码注释（不够直观）。
   - 仅使用docs/API.md（内容太杂乱）。

---

## 相关文档

- [架构总览](./ARCHITECTURE.md)
- [详细设计](./DESIGN.md)
- [API契约](../api.yaml)