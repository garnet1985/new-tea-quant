#!/usr/bin/env python3
# Strategy 模块重构 TODO 列表

> 目标：在保持策略模块易懂、可扩展的前提下，完成 OO 化与钩子化的第一版实现。

---

## Phase 0：基础设施收拢（已完成 ✅）

1. **统一版本管理器**
   - [x] 抽取 `VersionManager`，集中管理：
     - 枚举器版本：`opportunity_enums/{test|pool}/{version_id}/`
     - 价格因子模拟器：`results/simulations/price_factor/{version_id}/`
     - 资金分配模拟器：`results/capital_allocation/{version_id}/`
   - [x] 提供统一接口：`create_*_version(...)` / `resolve_*_version(...)` / `resolve_pool_version(...)`
   - [x] 简化版本目录命名（移除时间戳，只保留版本号）

2. **统一结果路径管理**
   - [x] 新增 `ResultPathManager`，负责版本目录下的文件路径：
     - `0_session_summary.json`
     - `trades.json`
     - `portfolio_timeseries.json`
     - `summary_strategy.json`
     - `metadata.json`
     - `{stock_id}.json`
   - [x] 将 PriceFactor / CapitalAllocation 两个模拟器中的路径拼接迁移到该 manager

3. **数据加载与事件流**
   - [x] 实现 `DataLoader`：
     - [x] 统一加载 `*_opportunities.csv` / `*_targets.csv`
     - [x] 提供带缓存的 `load_opportunities_and_targets(...)`
     - [x] 提供 `build_event_stream(...)` 构建资金分配用的 `List[Event]`
   - [x] 使用 `Event` dataclass 表达时间线事件（`trigger` / `target`）

---

## Phase 1：Settings 与数据模型（已完成 ✅）

1. **Settings 对象化**
   - [x] `BaseSettings` / `StrategySettings`：
     - [x] 从 `settings` 字典构建对象视图
     - [x] 提供 `validate_base_settings()` 等按需校验方法
     - [x] 提供 `get_data_config()` / `get_sampling_config()` / `get_goal_config()` 等便捷访问
   - [ ] 针对各子模块（枚举器 / 模拟器 / 资金分配）补充更细的验证方法（如时间范围、pool_version 格式等）- 可选增强

2. **核心数据模型 dataclass 化**
   - [x] `Opportunity`：带 `check_targets()` / `settle()` 等实例方法
   - [x] `Event`：资金分配时间线事件
   - [x] `Account` / `Position`：资金账户与持仓
   - [x] `Investment` / `Trade`：投资与成交记录
   - [ ] 收敛模拟器内部对原始 dict 的直接操作，尽量通过上述 dataclass 的方法完成计算 - 可选优化

---

## Phase 2：模拟器结构与钩子系统（已完成 ✅）

1. **BaseStrategyWorker 钩子扩展**
   - [x] 在 `BaseStrategyWorker` 中统一声明所有"可选钩子"方法：
     - [x] 枚举阶段：`on_init / on_before_scan / on_after_scan / on_before_simulate / on_after_simulate`
     - [x] 价格因子模拟器相关：
       - [x] `on_price_factor_before_process_stock(stock_id, opportunities, config) -> None`
       - [x] `on_price_factor_after_process_stock(stock_id, stock_summary, config) -> Dict`
       - [x] `on_price_factor_opportunity_trigger(opportunity, config) -> Dict`
       - [x] `on_price_factor_target_hit(target, opportunity, config) -> Dict`
     - [x] 资金分配模拟器相关：
       - [x] `on_capital_allocation_before_trigger_event(event, account, config) -> Dict`
       - [x] `on_capital_allocation_after_trigger_event(event, trade, account, config) -> Dict`
       - [x] `on_capital_allocation_before_target_event(event, account, config) -> Dict`
       - [x] `on_capital_allocation_after_target_event(event, trade, account, config) -> Dict`
       - [x] `on_capital_allocation_calculate_shares_to_buy(event, account, config, default_shares) -> Optional[int]`
       - [x] `on_capital_allocation_calculate_shares_to_sell(event, position, config, default_shares) -> Optional[int]`

2. **SimulatorHooksDispatcher 实现**
   - [x] 在 `components/simulator/base/` 中新增：
     - [x] `SimulatorHooksDispatcher`：
       - [x] 按 `strategy_name` 动态加载 `userspace.strategies.{name}.strategy_worker`
       - [x] 查找继承自 `BaseStrategyWorker` 的子类
       - [x] 使用最小 `job_payload` 创建实例
       - [x] 提供 `call_hook(hook_name, *args, **kwargs)`，自动处理"未重写"与异常

3. **将钩子接入 PriceFactorSimulator**
   - [x] 在 `PriceFactorSimulatorWorker` 中：
     - [x] 初始化 `SimulatorHooksDispatcher(strategy_name)`
     - [x] 在单股处理前后调用：
       - [x] `on_price_factor_before_process_stock(...)`
       - [x] `on_price_factor_after_process_stock(...)`
     - [x] 在机会与目标处理时调用：
       - [x] `on_price_factor_opportunity_trigger(...)`
       - [x] `on_price_factor_target_hit(...)`

4. **将钩子接入 CapitalAllocationSimulator**
   - [x] 在 `CapitalAllocationSimulator` 中：
     - [x] 在 `run()` 时创建 `self.hooks_dispatcher = SimulatorHooksDispatcher(strategy_name)`
     - [x] 在 `_handle_trigger_event()` 中：
       - [x] 触发前：`on_capital_allocation_before_trigger_event(...)`
       - [x] 计算默认买入股数后：`on_capital_allocation_calculate_shares_to_buy(...)`
       - [x] 生成 trade 后：`on_capital_allocation_after_trigger_event(...)`
     - [x] 在 `_handle_target_event()` 中：
       - [x] 触发前：`on_capital_allocation_before_target_event(...)`
       - [x] 计算默认卖出股数后：`on_capital_allocation_calculate_shares_to_sell(...)`
       - [x] 生成 trade 后：`on_capital_allocation_after_target_event(...)`

5. **示例 StrategyWorker**
   - [x] 在 `userspace/strategies/example/strategy_worker.py` 中：
     - [x] 演示最小实现（仅 scan_opportunity）
   - [ ] 演示一个价格因子钩子（例如根据信号强度标记机会）- 可选增强
   - [ ] 演示一个资金分配钩子（例如基于信号强度调整买入股数）- 可选增强

---

## Phase 3：Scanner 模块（已完成 ✅）

1. **Scanner 基础设施**
   - [x] 扩展 `ScannerSettings`：添加 `use_strict_previous_trading_day` 和 `max_cache_days`
   - [x] 实现 `ScanDateResolver`：日期解析逻辑（strict vs non-strict）
   - [x] 实现 `ScanCacheManager`：CSV 缓存读写 + 自动清理
   - [x] 定义 `BaseOpportunityAdapter` 接口和 `AdapterDispatcher`
   - [x] 实现 `Scanner` 主类：整合所有组件 + 多进程扫描
   - [x] 实现 `ConsoleAdapter` 示例：打印机会 + 历史胜率统计
   - [x] 实现 `HistoryLoader`：加载历史模拟结果并计算统计

---

## Phase 4：API 与文档对齐（待完成）

1. **对外 API 收敛**
   - [ ] 为枚举器、模拟器和扫描器提供统一入口：
     - [x] `OpportunityEnumerator.enumerate(...)` - 已实现
     - [x] `PriceFactorSimulator.run(strategy_name)` - 已实现
     - [x] `CapitalAllocationSimulator.run(strategy_name)` - 已实现
     - [x] `Scanner.scan()` - 已实现（需要传入 data_manager）
   - [ ] 在 `strategy_manager.py` 或上层 BFF 中提供统一调用示例

2. **文档更新**
   - [ ] 更新 `ARCHITECTURE_DESIGN.md` 与 `DESIGN.md`，将最终实现与设计对齐
   - [ ] 为 StrategyWorker 钩子编写一份"方法一览表 + 调用时机"文档
   - [ ] 在 README / Quick Start 中加入一条从"写一个策略"到"跑完整回测"的流水线示例

---

## 说明

- 本 TODO 列表只针对 **Strategy 模块第一版 OO + 钩子化实现**，未来若引入 MachineLearning / ParameterOptimizer 等模块，可在此基础上追加新的 Phase。
- 当前阶段不考虑向前兼容，目标是先把"第一版干净的结构"搭起来，再在此之上稳定演进。
- **已完成的核心功能**：基础设施、Settings、数据模型、钩子系统、Scanner 模块
- **待完成**：API 收敛、文档更新（可选增强）
