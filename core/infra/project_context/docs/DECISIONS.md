# Project Context 决策记录

**模块版本：** `0.2.0`

---

## 决策 1：无状态 Manager + 轻量 Facade

1. **背景（Context）**  
   路径、文件、配置多为无副作用查询，不宜在 Facade 内持有长生命周期状态。

2. **决策（Decision）**  
   `PathManager` / `FileManager` / `ConfigManager` 均为静态、无状态工具；`ProjectContextManager` 仅组合三者并暴露 `path` / `file` / `config` 引用。

3. **理由（Rationale）**  
   易测试、可并行调用、职责边界清晰。

4. **影响（Consequences）**  
   无全局单例；调用方自行缓存若需要。

5. **备选方案（Alternatives）**  
   带状态的「项目单例」持有已打开资源（增加生命周期与测试成本）。

---

## 决策 2：对外统一使用 `pathlib.Path`

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

## 决策 3：项目根目录统一发现与缓存

1. **背景（Context）**  
   各模块自行推断根目录时，在测试、脚本、IDE 下行为不一致。

2. **决策（Decision）**  
   `PathManager.get_root()` 自包路径向上查找根标记（`.git`、`pyproject.toml` 等），命中后写入 `_root_cache`。

3. **理由（Rationale）**  
   行为一致；首次遍历后 O(1)。

4. **影响（Consequences）**  
   极罕见布局若无标记则走 fallback 父链。

5. **备选方案（Alternatives）**  
   仅 `os.getcwd()`（不可靠）。

---

## 决策 4：配置格式与合并集中在 `ConfigManager`

1. **背景（Context）**  
   JSON 与 Python 配置、默认与用户合并逻辑曾分散实现。

2. **决策（Decision）**  
   支持 JSON 与 Python（`importlib` 加载）；`load_with_defaults` + 内部 `_deep_merge_config` 处理 `deep_merge_fields` / `override_fields`；`load_core_config` 约定 `default_config` + `user_config` 文件名。

3. **理由（Rationale）**  
   合并语义一处维护；业务按名选用加载器。

4. **影响（Consequences）**  
   复杂合并规则继续在 `ConfigManager` 演进。

5. **备选方案（Alternatives）**  
   各业务自写合并（重复与不一致）。

---

## 决策 5：温和失败（缺文件不抛）

1. **背景（Context）**  
   可选文件未创建时不应阻断探索性流程。

2. **决策（Decision）**  
   `find_file` 返回 `None`，`find_files` 返回 `[]`，读失败返回 `None`；用户配置缺失时 `load_with_defaults` 退回默认。

3. **理由（Rationale）**  
   Infra 提供原子能力；「是否必填」由上层定义。

4. **影响（Consequences）**  
   调用方需处理空值。

5. **备选方案（Alternatives）**  
   一律抛错（对脚手架不友好）。

---

## 决策 6：保留 Facade 与直接使用 Manager

1. **背景（Context）**  
   工具脚本或单测可能只需 `ConfigManager`。

2. **决策（Decision）**  
   对外仍导出 `PathManager`、`FileManager`、`ConfigManager`；推荐业务用 `ProjectContextManager`，但不强制。

3. **理由（Rationale）**  
   降低耦合与测试桩成本。

4. **影响（Consequences）**  
   两种导入方式长期并存。

5. **备选方案（Alternatives）**  
   仅暴露 Facade（限制高级用法）。

---

## 相关文档

- [架构总览](./ARCHITECTURE.md)
- [详细设计](./DESIGN.md)
- [API](./API.md)
