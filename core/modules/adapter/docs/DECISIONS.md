# Adapter 设计决策

**版本：** `0.2.0`

---

## 决策 1：userspace 包路径与目录名一致

**背景（Context）**  
需要在不修改 core 的前提下扩展「扫描完成后」的行为。

**决策（Decision）**  
约定 `userspace/adapters/<name>/adapter.py`，导入路径为 `userspace.adapters.<name>.adapter`；策略配置里只写 `<name>`。

**理由（Rationale）**  
与数据源、策略等 userspace 扩展方式一致，且可用标准 `importlib` 加载。

**影响（Consequences）**  
目录名即公开标识符，重命名 adapter 需同步改配置。

**备选方案（Alternatives）**  
在配置中写完整模块路径：更灵活但更冗长，当前未采用。

---

## 决策 2：模块内第一个合法子类即实现

**背景（Context）**  
同一 `adapter.py` 可能定义多个类，`inspect.getmembers` 顺序不保证直观。

**决策（Decision）**  
`validate_adapter` 与 `AdapterDispatcher._load_adapter_class` 均取 **第一个** 满足「继承 `BaseOpportunityAdapter` 且非基类」的类。

**理由（Rationale）**  
实现简单，且鼓励每个 adapter 文件只放一个主实现类。

**影响（Consequences）**  
多子类并存时行为依赖枚举顺序；扩展点文档要求「单主类」。

**备选方案（Alternatives）**  
约定类名后缀或显式注册表；未实现以保持加载逻辑最小。

---

## 决策 3：HistoryLoader 放在 adapter 包内

**背景（Context）**  
控制台等 adapter 需要展示历史模拟统计。

**决策（Decision）**  
提供 **`HistoryLoader`** 静态工具类，内部依赖 **`modules.strategy`** 的版本与路径管理器读取 JSON。

**理由（Rationale）**  
与「展示侧」常见需求放在一起，避免每个 userspace adapter 重复解析路径。

**影响（Consequences）**  
`modules.adapter` 对 `modules.strategy` 存在硬依赖；无策略结果时方法返回 `None`，调用方需容错。

**备选方案（Alternatives）**  
将加载逻辑完全迁入 `strategy` 或独立 `results` 子模块；当前以复用现有结果布局为主。

---

## 决策 4：分发与兜底放在 strategy.Scanner

**背景（Context）**  
扫描管线末尾需要统一调用 adapter。

**决策（Decision）**  
运行时调度由 **`AdapterDispatcher`**（strategy 包）实现；全部失败或无配置时调用 **`BaseOpportunityAdapter.default_output`**。

**理由（Rationale）**  
Scanner 已持有机会列表与上下文，避免在 `modules.adapter` 再引一层编排。

**影响（Consequences）**  
阅读「端到端行为」需同时看 strategy 的 dispatcher 与本模块基类。

**备选方案（Alternatives）**  
将 `AdapterDispatcher` 迁入 `modules.adapter`：会减少 strategy 体积，但会加深 adapter 对扫描管线的依赖，当前未采用。
