# Discovery 决策记录

**模块版本：** `0.2.0`

---

## 决策 1：将自动发现收敛为独立 infra 模块

1. **背景（Context）**  
   多处业务代码重复「遍历包 → import → 过滤子类/对象」逻辑，行为与日志不一致。

2. **决策（Decision）**  
   在 `core/infra/discovery` 提供通用发现能力，供各域按需配置使用。

3. **理由（Rationale）**  
   发现属于横切基础设施；集中实现便于统一缓存、日志与容错策略。

4. **影响（Consequences）**  
   新增模块与测试；调用方逐步以本模块替代手写扫描。

5. **备选方案（Alternatives）**  
   各业务模块内复制工具函数（难以统一演进）；或依赖第三方插件框架（引入额外约束）。

---

## 决策 2：拆分 `ClassDiscovery` 与 `ModuleDiscovery`

1. **背景（Context）**  
   「找子类」与「读模块级常量」的输入、过滤与失败语义不同，混在一个类中会导致 API 分支过多。

2. **决策（Decision）**  
   类发现与模块对象发现分属两个类型；模块侧以静态方法为主，无实例缓存。

3. **理由（Rationale）**  
   职责单一、类型提示清晰，文档与示例可按场景分开。

4. **影响（Consequences）**  
   两个源文件；调用方根据是否基于继承筛选选择入口。

5. **备选方案（Alternatives）**  
   单一 `Discovery` 类 +枚举模式参数（表面统一，实际难读）。

---

## 决策 3：使用 `DiscoveryConfig` 承载规则

1. **背景（Context）**  
   基类、路径模式、过滤与键提取若全部摊平为函数参数，复用与测试成本高。

2. **决策（Decision）**  
   以数据类 `DiscoveryConfig` 描述规则，`ClassDiscovery` 仅依赖该配置运行。

3. **理由（Rationale）**  
   配置可组合、可快照；同一配置可在测试与生产中复用。

4. **影响（Consequences）**  
   `ClassDiscovery` 构造必须传入配置；便捷场景用 `discover_subclasses` 封装。

5. **备选方案（Alternatives）**  
   全局可变配置或 kwargs 长列表（不利于显式与静态检查）。

---

## 决策 4：`ClassDiscovery` 默认缓存且可清理

1. **背景（Context）**  
   启动阶段可能对同一包多次查询；重复 import 与反射成本明显。

2. **决策（Decision）**  
   `discover(..., use_cache=True)` 时按 `base_module_path` 缓存 `DiscoveryResult`；提供 `clear_cache`。

3. **理由（Rationale）**  
   默认路径符合「一次扫描、多次使用」；测试与热加载场景可显式失效缓存。

4. **影响（Consequences）**  
   多进程或代码热替换需调用方自行清理或禁用缓存；`ModuleDiscovery` 不缓存。

5. **备选方案（Alternatives）**  
   每次全量扫描（简单但慢）；全局进程外缓存（超出本模块范围）。

---

## 决策 5：发现过程 fail-soft

1. **背景（Context）**  
   userspace 扩展可能未就绪或偶发语法错误；发现用于装配扩展时不应拖垮主流程。

2. **决策（Decision）**  
   单个子模块导入或属性读取失败时记录日志并跳过；整体返回已收集结果。

3. **理由（Rationale）**  
   与「可选插件」模型一致；问题可通过日志排查。

4. **影响（Consequences）**  
   调用方必须处理「结果为空或缺项」；需要 strict 模式时应在业务层额外校验。

5. **备选方案（Alternatives）**  
   首次失败即抛异常（调试友好但损害可用性）。

---

## 决策 6：约定式模块路径模式

1. **背景（Context）**  
   扩展目录结构在多数场景下稳定，完整列举模块路径冗长易错。

2. **决策（Decision）**  
   通过 `module_name_pattern` / `module_pattern` 的 `str.format` 占位符 `base_module`、`name`（及路径 API 的 `name`）生成实际模块路径。

3. **理由（Rationale）**  
   减少配置量并鼓励统一目录约定。

4. **影响（Consequences）**  
   非约定目录需自定义 pattern 或改用 `discover_modules_by_path`。

5. **备选方案（Alternatives）**  
   仅支持显式模块列表（灵活但维护成本高）。

---

## 相关文档

- [架构总览](./ARCHITECTURE.md)
- [详细设计](./DESIGN.md)
- [API](./API.md)
