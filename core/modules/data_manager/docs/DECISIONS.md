# Data Manager 设计决策

**版本：** `0.2.0`

---

## 决策 1：Facade 与单例

**背景（Context）**  
多处需要访问同一数据库与同一套表模型。

**决策（Decision）**  
`DataManager` 默认 **进程内单例**（线程安全锁 + 双重检查），可选 **`force_new`** 用于测试或隔离。

**理由（Rationale）**  
减少连接与表注册重复初始化成本。

**影响（Consequences）**  
多进程必须每进程各自创建 `DataManager`（内存不共享）。

---

## 决策 2：表定义放在 `core/tables` 与 `userspace/tables`

**背景（Context）**  
历史上曾将 Model 散落在模块内 `base_tables/`；现统一为 **按目录 + schema/model** 发现。

**决策（Decision）**  
递归发现 **`schema.py`**，按规则注册；core 表名强制 **`sys_`** 前缀。

**理由（Rationale）**  
与 DB 迁移、多用户扩展目录一致；避免未前缀表误入 core。

**影响（Consequences）**  
新增 core 表必须遵守命名与目录结构。

---

## 决策 3：领域服务显式嵌套，不提供隐式「总 load」

**背景（Context）**  
避免 `data_mgr.stock` 上堆积对所有子域的委托方法，导致职责不清。

**决策（Decision）**  
K 线、列表、标签等 **必须** 通过 **`data_mgr.stock.kline`**、**`data_mgr.stock.list`** 等子属性访问。

**理由（Rationale）**  
符合「Explicit is better than implicit」，便于搜索与测试。

**影响（Consequences）**  
调用链略长，但路径唯一。

---

## 决策 4：`get_table` 面向内部

**背景（Context）**  
外部若直接拿 Model，易绕过服务层约束与查询优化。

**决策（Decision）**  
`get_table` 文档语义为 **DataService 内部**；业务与策略代码优先走 **各 Service 的 load/save**。

**理由（Rationale）**  
稳定 API 边界，便于替换存储与 SQL 策略。

**影响（Consequences）**  
高级场景仍可 `get_table`，但不作为推荐路径。

---

## 决策 5：构造时自动 `initialize`

**背景（Context）**  
减少「忘记初始化」导致的运行时错误。

**决策（Decision）**  
**`__init__` 末尾调用 `initialize()`**；`initialize` **幂等**。

**理由（Rationale）**  
开箱即用；测试可 `reset_instance` 或 `force_new`。

**影响（Consequences）**  
导入即触发 DB 连接与表发现（在首次创建实例时）。
