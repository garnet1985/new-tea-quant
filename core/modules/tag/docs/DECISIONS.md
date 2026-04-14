# Tag 设计决策

**版本：** `0.2.0`

---

## 决策 1：实体型（`entity_based`）与通用型（`general`）标签目标

**背景（Context）**  
标签既需要按股票等实体逐只计算，也需要少量不绑定单实体的全局结果；配置层需可扩展且类型安全。

**决策（Decision）**  
引入 **`TagTargetType`**：**`ENTITY_BASED`** 与 **`GENERAL`**，由 **`ScenarioModel`** 与 Job 构建逻辑区分执行路径。

**理由（Rationale）**  
实体型与全局型的数据准备、并行粒度不同，显式分类避免隐式约定导致错误分片或空跑。

**影响（Consequences）**  
新增场景类型时需正确设置 target 类型，并与 **`TagManager`** 的实体列表解析保持一致。

---

## 决策 2：横截面（cross-sectional）类能力暂不纳入框架核心

**背景（Context）**  
全市场同一日截面上的排名、分位等依赖「当日多实体联合」视图，与当前「单实体 + as_of 历史切片」模型不同。

**决策（Decision）**  
不在本模块核心路径提供一等公民的 cross-sectional API；需要时由用户在 **`calculate_tag`** 内自行组合查询或缓存。

**理由（Rationale）**  
避免在 DataCursor 语义上叠加模糊的「全市场快照」契约，降低一致性与性能风险。

**影响（Consequences）**  
复杂横截面标签需更多自定义代码或预计算中间表；未来若引入需单独设计与 **`DECISIONS`** 增补。

---

## 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DESIGN.md](DESIGN.md)
- [API.md](API.md)
