## Strategy Simulator 设计文档

### 1. 目标与定位

- **目标**：在没有资金约束的前提下，基于枚举器（Opportunity Enumerator）的 枚举输出结果，对每只股票的机会进行价格驱动的模拟，评估“机会出现即买入 1 股，并持有到机会结束”的策略效果。
- **输入**：枚举器在 `sot/` 目录下的某个版本（opportunity_enums/sot/{version}）导出的机会与目标结果。
- **输出**：单股层面和策略整体层面的收益与统计指标，用于评估策略本身（不考虑资金管理和仓位分配）。

> 特点：  
> - 每只股票的模拟完全独立，可天然并行。  
> - 不考虑资金上限，单纯关注“价格路径 + 机会定义”本身的质量。  
> - 为 Capital Allocation Simulator 提供“纯策略表现”的参考基准。

---

### 2. 数据来源与输入格式

#### 2.1 数据来源

- 来自枚举器 枚举输出版本目录：
  - `app/userspace/strategies/{strategy_name}/results/opportunity_enums/sot/{version_dir}/`
  - 其中包含：
    - `{stock_id}_opportunities.csv`
    - `{stock_id}_targets.csv`
    - `metadata.json`（版本元信息）

#### 2.2 输入选择（枚举输出版本）

- 在 `settings.simulator.sot_version` 中配置：
  - 具体版本名：如 `"1_20260112_161317"`  
    - 若目录不存在 → 拒绝执行，记录错误日志。
  - `"latest"`：从 `sot/` 子目录下选择**版本号最大**的一个版本。

#### 2.3 机会与目标结构（逻辑视图）

以 `Opportunity` 和其 `completed_targets` 为核心：

- **机会主表（opportunities.csv，按 stock_id 区分文件）**：
  - `opportunity_id`: str，机会 ID（在枚举阶段生成，单股内唯一）
  - `stock_id`: str
  - `trigger_date`: str，触发日期（YYYYMMDD）
  - `trigger_price`: float，触发价格
  - `status`: str，`win` / `loss` / `open`
  - `roi`: float，最终加权 ROI
  - 其他策略相关字段（如指标值、分组标签等），对 Simulator 来说为附加信息。

- **目标结果表（targets.csv）**：
  - `opportunity_id`: str（外键）
  - `date`: str，分段结算日期
  - `price`: float，分段结算价格
  - `sell_ratio`: float，本段卖出比例（0~1）
  - `roi`: float，本目标对应 ROI（兼容字段）
  - 其他字段：`reason` 等。

> 约束：
> - 对于 Strategy Simulator，可以只依赖 `trigger_date / trigger_price` 以及 `completed_targets` 的 `date / price / sell_ratio`。

---

### 3. 时间窗口与过滤逻辑

#### 3.1 时间范围配置

- 在 `settings.simulator.start_date` / `settings.simulator.end_date` 中配置：
  - 若为空：
    - `start_date`：取该 枚举输出版本中所有机会 `trigger_date` 的最小值。
    - `end_date`：取该 枚举输出版本中所有机会及其 `completed_targets.date` 的最大值。

#### 3.2 机会筛选

对每只股票：

- 选出满足以下条件的机会：
  - `trigger_date >= start_date`
  - `trigger_date <= end_date`
- 对每个机会，使用其所有 `completed_targets`，但在时间分析中只考虑 `date <= end_date`。

---

### 4. 核心业务规则

#### 4.1 投资单位与资金假设

- **投资单位**：每个被采纳的机会，**买入 1 股**。
- **资金约束**：**无资金上限**：
  - 不模拟真实账户现金余额和保证金。
  - 只记录每个被触发的机会的盈亏表现。

#### 4.2 单股持仓约束

- 对于每只股票，同一时刻最多只持有 **一个机会对应的仓位**：
  - 若当前股票已有持仓（`shares > 0`），新机会默认**不再开仓**。
  - 若用户通过加仓钩子主动“平旧开新”，则以用户逻辑为准（详见钩子部分）。

#### 4.3 事件流与执行顺序（单股内部）

1. **构建事件列表**（per stock）：
   - 对筛选后的机会集合：
     - 为每个 `opportunity` 生成：
       - `trigger_event`: 在 `trigger_date` 发生。
       - 对于每个 `completed_target`：
         - `target_event`: 在 `target.date` 发生。
   - 将所有事件合并为时间轴：
     - 按 `date` 升序排序。
     - 同日多事件时：
       - 先按事件类型排序（可以采用：先处理分段结算，再处理新增机会，或反之；推荐**先结算再开仓**，以避免顺序偏差）。
       - 再按 `opportunity_id` 排序（自然顺序）。

2. **模拟逻辑**：
   - 维护单股状态 `position`：
     - `is_holding`: bool
     - `current_opportunity_id`: str | None
     - `shares`: int（起始为 0）
     - `avg_cost`: float
     - `realized_pnl`: float
   - 遍历事件：
     - **Trigger 事件**：
       - 若 `position.is_holding == False`：
         - 以 `trigger_price`（加上交易成本）买入 1 股：
           - `shares = 1`
           - `avg_cost = fill_price`
           - `current_opportunity_id = opp_id`
           - `is_holding = True`
       - 若 `position.is_holding == True`：
         - 默认**跳过**该机会（不参与）。
         - 在处理完默认逻辑后，调用钩子允许用户干预（例如强平旧机会换新机会）。
     - **Target 事件**（仅对 `current_opportunity_id` 对应的机会有效）：
       - 使用当前 `shares` 和 `avg_cost`，按 `sell_ratio` 模拟部分或全部卖出。
       - 由于 Strategy Simulator 默认只持有 1 股且不做资金预算，可采用简化模式：
         - 视 `sell_ratio` 为**完成比例**；若累积 `sell_ratio >= 1`，则本机会视为结束，平掉全部仓位。
       - 计算本段实现盈亏：
         - `segment_pnl = shares * sell_ratio * (sell_price - avg_cost) - fees`
       - 将 `segment_pnl` 计入 `realized_pnl`。
       - 若机会所有目标完成（`total_sell_ratio >= 1`）：
         - `shares = 0`
         - `is_holding = False`
         - `current_opportunity_id = None`

3. **日期与 T+1 约束**（可选简化）

- Strategy Simulator 为纯价格模拟，一般可忽略 T+1 对资金的影响（因为无资金池）。
- 若需要严格对齐业务语义，可记录：
  - 若目标日期距离 `trigger_date` 少于 1 个交易日，则可视为下一交易日记入收益（内部通过 DateUtils 封装）。

---

### 5. 钩子与可扩展行为

为了允许用户自定义行为（加仓 / 换机会等），Strategy Simulator 暴露一组钩子接口，位于用户策略目录，例如：

- 模块：`app/userspace/strategies/{strategy_name}/strategy_simulator_hooks.py`

#### 5.1 加仓钩子 on_add_position

- 签名（建议）：
  - `def on_add_position(opportunity, current_stage, position_snapshot) -> int:`
    - `opportunity`: 当前机会的完整字典信息。
    - `current_stage`: 当前阶段信息：
      - 若在 trigger 日：`{"type": "trigger", "date": ..., "price": ...}`
      - 若在 target 结算：`{"type": "target", "date": ..., "price": ..., "sell_ratio": ...}`
    - `position_snapshot`: 只读视图（当前 `shares`, `avg_cost`, `realized_pnl` 等）。
    - 返回值：
      - `> 0`：加仓股数（在当前价格成交，更新 `shares` 和 `avg_cost`）。
      - `0`：不加仓。
      - 负数：预留为高级行为（例如“减仓”），初期可不实现。

#### 5.2 换机会/强平钩子（选配）

- 可预留：
  - `def before_new_opportunity(new_opp, current_position) -> str:`
    - 决策当前持仓是否需要平掉以接纳新的机会：
      - 返回 `"keep"` / `"close_and_open_new"` / `"skip_new"`.

---

### 6. 输出与指标设计

#### 6.1 单股层面输出

- 对每只股票，输出结构（写入 `summary_stock.json` 中的条目）：
  - `stock_id`
  - `total_opportunities`: 总机会数
  - `participated_opportunities`: 实际参与机会数（触发且未被跳过）
  - `win_count`: 最终 ROI > 0 的机会数
  - `loss_count`: 最终 ROI <= 0 的机会数
  - `total_realized_pnl`: 所有参与机会的收益和
  - `avg_pnl_per_trade`
  - `max_drawdown`（若引入“虚拟账户权益曲线”）
  - 其它辅助指标：如胜率、盈亏比等。

#### 6.2 策略整体输出

- 在 `summary_strategy.json` 中聚合：
  - `total_stocks`
  - `total_participated_opportunities`
  - `global_win_rate`
  - `total_realized_pnl`
  - `avg_pnl_per_trade`
  - `pnl_distribution`：按股票 / 行业 / 市值分组的统计（可选）

---

### 7. 并发与执行流程

#### 7.1 并发模型

- 每只股票模拟流程彼此独立：
  - 输入：特定 stock 的 枚举输出 CSV
  - 输出：该 stock 的局部 summary + 交易记录
- 可复用现有多进程框架（类似 OpportunityEnumeratorWorker）：
  - 主进程负责编排：
    - 选择 枚举输出版本
    - 读取股票列表
    - 按股票构建作业列表
  - 子进程执行单股模拟，并将结果回传主进程。

#### 7.2 主流程概要

1. 解析 `settings.simulator`，确定：
   - `sot_version`、`start_date`、`end_date`
2. 加载 枚举输出版本目录，构建股票列表（与枚举器一致）
3. 为每只股票构建模拟任务（包含需要的路径与时间配置）
4. 使用 ProcessWorker 并行执行单股 Strategy Simulation
5. 聚合子结果，生成：
   - `trades.json`（可选，或分 per-stock 输出）
   - `summary_stock.json`
   - `summary_strategy.json`

---

### 8. 与 Capital Allocation Simulator 的关系

- Strategy Simulator 只解决“机会本身质量”的问题：
  - 不涉及资金分配、仓位管理。
- Capital Allocation Simulator 在此基础上引入真实资金约束：
  - 使用同一套 枚举输出数据和时间轴。
  - 但在全局账户维度上做交易决策。

