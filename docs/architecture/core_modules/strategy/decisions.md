# Strategy 模块重要决策记录

**版本：** 3.0  
**最后更新**: 2026-01-17

---

本文档记录了 Strategy 模块的重要架构设计决策，包括问题背景、决策理由和影响。

---

## 决策 1：四层架构设计 & 枚举层作为 SOT 缓存层

**问题**：如何组织 Scanner、Simulator、OpportunityEnumerator 的关系？为什么要单独拆出一个底层枚举器？

**决策**：采用四层架构，并将 **Layer 0（OpportunityEnumerator）** 明确定位为整个策略系统的「底层事实表（SOT）+ 回测缓存层」：
- **Layer 0（OpportunityEnumerator）**：完整枚举所有可能机会，一次计算、多次复用，为上层所有模拟与分析提供统一 SOT
- **Layer 1（Scanner）**：实时机会扫描，用于实盘提示
- **Layer 2（PriceFactorSimulator）**：价格因子模拟，验证信号质量
- **Layer 3（CapitalAllocationSimulator）**：资金分配模拟，真实资金约束

**理由**：
- **一次计算，多次复用**：昂贵的「全市场 on-bar 枚举」只在枚举层做一次；上层所有模拟（价格/资金）、分析工具和机器学习任务都直接复用同一份 SOT 结果
- **可追溯，便于调试**：每一个机会在 SOT 中都有完整记录，可以随时回溯到具体股票、具体日期的机会路径
- **天然对分析 & 机器学习友好**：SOT 本质上是结构化样本表，非常适合作为分析/建模的数据源
- **相当于回测缓存层**：把传统「on bar 回测」拆成「先枚举机会，再叠加模拟」，显著缩短策略迭代周期

**影响**：
- 清晰的职责分离，便于理解和维护
- 上层可以系统性复用下层输出（如 Simulators 使用 Enumerator 的 SOT 结果），避免重复计算
- 用户在文档和使用体验中会频繁感知到「一次枚举，多次复用」这一核心亮点

---

## 决策 2：完整枚举 vs 主线回测

**问题**：OpportunityEnumerator 和 Simulator 的区别是什么？

**决策**：OpportunityEnumerator 做完整枚举，Simulator 做主线回测。

**理由**：
- **完整枚举**：每天都扫描，同时追踪多个机会，输出所有可能路径（供 Allocation 使用）
- **主线回测**：无持仓时才扫描，同时只能持有 1 个，输出单一路径（策略验证）

**影响**：
- OpportunityEnumerator 输出数据量大（CSV 格式，高性能）
- Simulator 输出数据量小（JSON 格式，易读）

---

## 决策 3：价格层面 vs 资金层面分离

**问题**：PriceFactorSimulator 和 CapitalAllocationSimulator 的区别是什么？

**决策**：PriceFactorSimulator 只关注价格变化，CapitalAllocationSimulator 考虑真实资金约束。

**理由**：
- **价格层面**：快速验证信号质量，无资金约束，适合快速迭代
- **资金层面**：真实资金约束，考虑费用、持仓限制，适合完整回测

**影响**：
- 用户可以先使用 PriceFactorSimulator 快速验证，再使用 CapitalAllocationSimulator 完整回测
- 两个模拟器可以共享 SOT 结果，避免重复计算

---

## 决策 4：CSV vs JSON 存储

**问题**：OpportunityEnumerator 使用 CSV，其他组件使用 JSON，为什么？

**决策**：OpportunityEnumerator 使用 CSV，其他组件使用 JSON。

**理由**：
- **CSV（OpportunityEnumerator）**：
  - 数据量大（5K-500K 条记录）
  - 需要高性能（加载快，0.1-0.2 秒）
  - Excel 可直接打开，便于查看
- **JSON（Scanner/Simulators）**：
  - 数据量小（几百到几千条记录）
  - 需要结构化数据（嵌套对象、数组）
  - 便于程序处理

**影响**：
- OpportunityEnumerator 需要 CSV 读写逻辑
- 其他组件需要 JSON 序列化/反序列化

---

## 决策 5：多进程 vs 单进程

**问题**：哪些组件使用多进程，哪些使用单进程？

**决策**：
- **多进程**：Scanner、OpportunityEnumerator、PriceFactorSimulator（每只股票独立，适合并行）
- **单进程**：CapitalAllocationSimulator（需要全局账户状态，不适合并行）

**理由**：
- **多进程场景**：每只股票的处理相互独立，可以并行执行
- **单进程场景**：需要全局账户状态，按时间顺序执行，不适合并行

**影响**：
- 多进程组件需要序列化 job payload
- 单进程组件需要按时间顺序处理事件

---

## 决策 6：事件驱动 vs 逐日迭代

**问题**：CapitalAllocationSimulator 使用事件驱动还是逐日迭代？

**决策**：使用事件驱动方式。

**理由**：
- **事件驱动**：只处理有事件的日期（trigger/target），效率高
- **逐日迭代**：需要遍历所有日期，效率低

**影响**：
- 需要构建事件流（从 SOT CSV 构建 Event 列表）
- 需要按日期排序事件

---

## 决策 7：Settings 两层架构

**问题**：如何组织 Settings？使用继承还是组合？

**决策**：使用两层架构（BaseSetting + 组件视图）。

**理由**：
- **BaseSetting（StrategySettings）**：通用配置，所有模块共用
- **组件视图（如 OpportunityEnumeratorSettings）**：组件专用配置，组合而非继承
- **优势**：职责清晰，便于验证和补全默认值

**影响**：
- 每个组件需要定义自己的 Settings 视图
- 需要实现 `from_base()` 方法

---

## 决策 8：技术指标自动计算

**问题**：技术指标是在框架层面自动计算，还是用户手动计算？

**决策**：框架层面自动计算。

**理由**：
- **统一管理**：框架统一计算，避免重复代码
- **性能优化**：一次性计算所有指标，避免重复计算
- **易于使用**：用户直接使用 `kline["ma5"]`，无需手动计算

**影响**：
- 需要在 `StrategyWorkerDataManager` 中实现指标计算逻辑
- 需要解析 `data.indicators` 配置

---

## 决策 9：数据过滤策略

**问题**：如何避免"上帝模式"问题（计算时看到未来数据）？

**决策**：框架层面强制过滤到 `as_of_date`。

**理由**：
- **保证计算一致性**：框架层面过滤，保证所有 StrategyWorker 都遵循相同规则
- **简化用户代码**：用户无需关心数据过滤，只需关注业务逻辑
- **减少出错可能**：避免用户忘记过滤数据

**影响**：
- 每次调用 `scan_opportunity()` 前都需要过滤数据（性能开销可接受）
- 用户无法访问未来数据（这是期望的行为）

---

## 决策 10：版本管理设计

**问题**：如何管理 SOT 版本和模拟器版本？

**决策**：使用统一的 VersionManager，支持版本目录和版本号。

**理由**：
- **版本对比**：可以对比不同版本的结果
- **版本清理**：可以清理旧版本，节省空间
- **版本追溯**：可以追溯历史版本

**影响**：
- 需要实现版本目录创建和解析逻辑
- 需要支持 "latest"、具体版本号、"test/latest" 等格式

---

**文档结束**
