# Data Cursor 设计决策

**版本：** `0.2.0`

---

## 决策 1：只消费已物化的 `contract.data`

**背景（Context）**  
游标不应隐式触发 IO。

**决策（Decision）**  
构造时若 **`data` 为空** 直接 **`ValueError`**。

**理由（Rationale）**  
职责分离：加载由 **`data_contract`** / **`data_manager`** 完成。

**影响（Consequences）**  
调用方必须保证 **`load`** 顺序正确。

---

## 决策 2：累计前缀而非仅增量

**背景（Context）**  
策略侧习惯拿到「截至 T 的全历史」做指标。

**决策（Decision）**  
**`until`** 返回的 **`acc`** 为 **自起点到当前 as_of 的累计行**（在同一 **`reset`** 周期内持续增长）。

**理由（Rationale）**  
避免上层每次自行 merge 历史。

**影响（Consequences）**  
内存随 as_of 推进增长；长历史需注意窗口策略（上层裁剪）。

---

## 决策 3：非时序源不参与时间切片

**背景（Context）**  
股票列表、静态映射等无统一时间轴。

**决策（Decision）**  
**`NON_TIME_SERIES`** 或 **`time_field` 为空** 时，**`until`** 始终输出 **全量 `rows`**。

**理由（Rationale）**  
与 **`ContractType`** 语义一致。

**影响（Consequences）**  
调用方勿依赖非时序源的「按日变化」。

---

## 决策 4：独立小模块 + Manager命名注册

**背景（Context）**  
Strategy与 Tag 均需同类能力。

**决策（Decision）**  
 **`DataCursor`** 纯逻辑；**`DataCursorManager`** 按 **`name`** 存取，便于多会话或测试替换。

**理由（Rationale）**  
避免把游标状态塞进全局单例。

**影响（Consequences）**  
**`name`** 冲突会覆盖注册（同 manager 实例内）。
