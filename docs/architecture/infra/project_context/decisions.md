# Project Context 重要决策记录

本文档归档 Project Context 模块在设计与演进过程中的关键决策，便于后续迭代时参考。

---

## Decision 1：使用无状态 Manager + Facade 组合

**日期：** 2025-XX-XX  
**状态：** 已实施

### 背景

- 早期实现中曾考虑让 `ProjectContextManager` 持有大量运行时状态（如缓存、打开的文件句柄等）
- 但实际需求更多是「查路径」「读文件」「合并配置」这类纯函数式操作

### 方案

- 将能力拆分为三个无状态工具类：
  - `PathManager`：路径管理
  - `FileManager`：文件操作
  - `ConfigManager`：配置加载与合并
- `ProjectContextManager` 只作为轻量 Facade，将三者组合起来提供统一入口

### 理由

1. **易测试**：无状态工具类更容易单元测试，也便于在不同环境下复用
2. **低风险**：避免在全局上下文中持有复杂状态或长生命周期资源
3. **职责清晰**：路径 / 文件 / 配置三类职责明确分离，便于独立演进

---

## Decision 2：统一使用 `pathlib.Path`

**日期：** 2025-XX-XX  
**状态：** 已实施

### 背景

- 早期代码中 `os.path` 与字符串路径混用，导致：
  - Path 拼接容易出错（`"/"` 与 `os.path.join` 混用）
  - 类型不统一，不利于静态检查与重构

### 方案

- `PathManager` / `FileManager` / `ConfigManager` 的对外接口全部使用 `pathlib.Path`
- 仅在必要与外部库交互时（如某些第三方库只接受字符串路径）做 `str(path)` 转换

### 理由

1. **API 统一**：内部路径表示统一为 `Path`，业务代码不再关心字符串拼接细节
2. **可读性好**：`path / "subdir" / "file"` 明显优于字符串拼接
3. **跨平台性更好**：交由 `Path` 处理不同平台的分隔符与规则

---

## Decision 3：项目根目录的发现与缓存策略

**日期：** 2025-XX-XX  
**状态：** 已实施

### 背景

- 不同模块用不同办法推断项目根目录：
  - 有的依赖 `os.getcwd()`
  - 有的从当前文件向上遍历
  - 有的硬编码「多级 `..` 回退」
- 在测试、脚本、IDE 中表现不一致

### 方案

- 在 `PathManager.get_root()` 中实现统一的项目根发现逻辑：
  1. 从当前文件所在目录向上遍历父目录
  2. 直到发现「根标记」之一：`.git`、`pyproject.toml`、`setup.py`、`README.md` 等
  3. 找到后缓存结果，后续调用直接返回缓存

### 理由

1. **行为一致**：所有模块都基于同一套规则推断项目根
2. **性能可控**：向上遍历只在首次调用发生，之后走缓存
3. **易理解**：根标记清晰直观，符合多数 Python 项目约定

---

## Decision 4：配置文件格式与合并策略

**日期：** 2025-XX-XX  
**状态：** 已实施

### 背景

- 不同模块使用不同配置格式：
  - 有的只支持 JSON
  - 有的直接读 Python 模块
- 默认配置与用户配置的合并逻辑分散在各处，存在重复实现与行为不一致问题

### 方案

- `ConfigManager` 统一支持两种配置源：
  - JSON 文件（通常位于 `core/`，作为默认配置）
  - Python 文件（如 `userspace/strategies/<name>/settings.py`，作为用户配置）
- 提供统一的 `load_with_defaults` 接口，内部使用 `deep_merge_config` 支持：
  - `deep_merge_fields`：指定需要做嵌套合并的字段（如 `params`）
  - `override_fields`：指定用户配置需要完全覆盖默认配置的字段（如 `dependencies`）

### 理由

1. **行为一致**：所有模块遵循相同的「默认 + 用户」合并策略
2. **灵活扩展**：既保留 JSON 易读、易生成的优势，又允许用户用 Python 写复杂逻辑
3. **减少重复**：避免在各模块中复制配置合并代码

---

## Decision 5：错误处理策略 —— 尽量温和失败

**日期：** 2025-XX-XX  
**状态：** 已实施

### 背景

- 某些早期实现中，对于「文件不存在」「目录不存在」等情况直接抛异常
- 在探索性开发 / 用户刚搭环境时，这种行为体验较差

### 方案

- 在 Project Context 相关 API 中统一采用「温和失败」策略：
  - `find_file` 找不到返回 `None`
  - `find_files` 找不到返回空列表
  - `file_exists` / `dir_exists` 返回 `False`
  - `load_with_defaults` 在用户配置缺失时只使用默认配置，不视为错误
- 真正的「配置必需」语义交由上层模块表达，而非 Project Context 强制

### 理由

1. **提升开发体验**：避免因为某个可选文件未创建就导致整个流程中断
2. **职责清晰**：是否「必须存在」由业务层决定，Infra 层只提供原子能力
3. **更易调试**：返回空值往往比直接抛异常更容易被上层捕获并打印上下文

---

## Decision 6：保留 Facade 与底层 Manager 的直接使用能力

**日期：** 2025-XX-XX  
**状态：** 已实施

### 背景

- 部分高级用例需要更精细的控制，例如：
  - 只想用 `ConfigManager`，不希望引入完整的 `ProjectContextManager`
  - 在某些工具脚本中，需要特别控制路径起点

### 方案

- 推荐在业务代码中使用 `ProjectContextManager`：
  - 便于统一管理与重构
  - 代码语义更清晰（`ctx.path.*` / `ctx.file.*` / `ctx.config.*`）
- 但同时保留直接引入单个 Manager 的能力：
  - `from app.core.infra.project_context import PathManager, FileManager, ConfigManager`

### 理由

1. **兼顾易用性与灵活性**：常规场景用 Facade，高级场景可以按需组合
2. **不锁死演进路线**：未来可以在不破坏底层 Manager 的前提下演进 Facade 行为
3. **降低耦合**：某些工具模块可以只依赖 Path / Config 中的一部分能力

---

## 相关文档

- 架构设计文档：`architecture/infra/project_context/architecture.md`
- 设计细节：`core/infra/project_context/DESIGN.md`
