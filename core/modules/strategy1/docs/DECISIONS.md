# Strategy 设计决策

**版本：** `0.2.0`

---

## 决策 1：四层架构，枚举层为「事实表 + 缓存」

**背景（Context）**  
扫描、价格验证、资金回测若各自重复跑全市场 on-bar，成本过高且结果难对齐。

**决策（Decision）**  
采用 **Layer 0～3**；**OpportunityEnumerator** 产出统一 **枚举输出（CSV）**，作为下游模拟与分析的可复用事实表。

**理由（Rationale）**  
一次枚举、多次复用；可追溯至具体标的与日期；利于 ML 与分析取数。

**影响（Consequences）**  
用户需理解枚举与主线 simulate 的分工；磁盘上同时存在 CSV 与 JSON 两类工件。

---

## 决策 2：完整枚举 vs 主线 simulate

**背景（Context）**  
业务上既需要「所有可能机会」又需要「单持仓叙事」的验证路径。

**决策（Decision）**  
Enumerator **不**按单持仓剪枝；**`BaseStrategyWorker` simulate** 按日推进、同一时间窗口内典型单机会追踪。

**理由（Rationale）**  
前者服务组合级模拟与数据科学；后者服务策略逻辑快速迭代。

**影响（Consequences）**  
枚举数据量远大于 simulate JSON；二者用途不同，不可混读。

---

## 决策 3：价格模拟与资金模拟分离

**背景（Context）**  
信号质量评估与资金约束下的 PnL 关注点不同。

**决策（Decision）**  
**PriceFactorSimulator** 聚焦价格路径与 ROI；**CapitalAllocationSimulator** 引入账户、费用与分配策略。

**理由（Rationale）**  
先验证信号再引入资金复杂度，降低调参维度。

**影响（Consequences）**  
两步模拟均依赖枚举输出；参数与 settings 块分离维护。

---

## 决策 4：CSV（枚举）与 JSON（扫描 / simulate管理器路径）

**背景（Context）**  
大表性能与嵌套结构可读性需求并存。

**决策（Decision）**  
Enumerator 用 **CSV**；**StrategyManager** 的 scan/simulate 结果用 **JSON**。

**理由（Rationale）**  
批量行式写入与加载；小体量结构化对象便于 Adapter 与调试。

**影响（Consequences）**  
两套 IO 与路径约定，由 **OpportunityService** / **DataLoader** 分别封装。

---

## 决策 5：并发策略

**背景（Context）**  
CPU 利用与全局一致性之间的权衡。

**决策（Decision）**  
扫描、枚举、价格模拟 **多进程**；资金模拟 **单进程**（全局账户序）。

**理由（Rationale）**  
独立股票任务易并行；账户状态需确定性顺序。

**影响（Consequences）**  
Job payload 必须可 pickle；资金模拟耗时可能成为大策略瓶颈。

---

## 决策 6：资金模拟采用事件驱动

**背景（Context）**  
逐日历日遍历稀疏事件浪费严重。

**决策（Decision）**  
**CapitalAllocationSimulator** 以 **Event** 流驱动为主干。

**理由（Rationale）**  
只在有触发/目标达成等事件时推进组合逻辑。

**影响（Consequences）**  
**DataLoader** 需稳定地将 CSV 转为有序事件。

---

## 决策 7：Settings 分块 dataclass

**背景（Context）**  
单一大 dict 难校验、难默认值管理。

**决策（Decision）**  
顶层 **`StrategySettings`** 组合各 **`Strategy*Settings`** 块，统一 **`validate`**。

**理由（Rationale）**  
职责清晰，错误定位可到具体配置节。

**影响（Consequences）**  
新增配置域需同时扩展 dataclass 与文档。

---

## 决策 8：指标由框架在 DataManager 路径预计算

**背景（Context）**  
用户重复算指标易错且慢。

**决策（Decision）**  
**`StrategyDataManager`** 按 **`data.indicators`** 拉取并写入 kline 行字段。

**理由（Rationale）**  
与 DataContract / 游标一体，保证 as_of 一致。

**影响（Consequences）**  
依赖 **`modules.indicator`**；指标配置变更需重载数据。

---

## 决策 9：框架强制 as_of 数据切片

**背景（Context）**  
防止无意使用未来数据。

**决策（Decision）**  
Simulate 路径通过 **`get_data_until`** 提供「截至当日」数据。

**理由（Rationale）**  
统一约束，减轻用户心智负担。

**影响（Consequences）**  
极个别需「已知未来」的实验须自行绕过（不推荐）。

---

## 决策 10：版本管理统一由 VersionManager

**背景（Context）**  
多轮枚举与模拟需对比与清理。

**决策（Decision）**  
**VersionManager** 创建/解析版本目录，支持 `latest` 与显式版本 id。

**理由（Rationale）**  
路径规则集中，CLI 与模拟器行为一致。

**影响（Consequences）**  
用户需了解 `output` / `test` 等目录语义与 `base_version` 配置。

---

## 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DESIGN.md](DESIGN.md)
- [API.md](API.md)
