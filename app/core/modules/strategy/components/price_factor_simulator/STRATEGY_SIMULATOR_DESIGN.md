## PriceFactorSimulator 设计文档

### 1. 目标与定位

- **定位**: 基于枚举器 SOT 结果的、仅关注价格路径的单股「价格因子」模拟器（PriceFactorSimulator）。
- **核心思想**:
  - 每只股票独立模拟，**不考虑资金约束**。
  - 当机会出现时，以 **1 股** 为单位入场。
  - 在机会生命周期内追踪其完成/失败情况，统计策略表现。
  - 提供 **加仓钩子**，允许用户在默认规则之上自定义加仓逻辑。
- **典型用途**:
  - 快速验证“只看价格/机会本身”的策略质量（不考虑资金管理）。
  - 与 Capital Allocation Simulator 对比，隔离“资金分配”与“价格因子/信号质量”的影响。

---

### 2. 输入与输出

#### 2.1 输入数据

- **来源**: `results/opportunity_enums/sot/{version_dir}/`
- **版本选择**:
  - 在 `settings.simulator.sot_version` 中显式配置:
    - 具体版本号: 如 `"1_20260112_161317"`，若不存在则拒绝执行。
    - `"latest"`: 选择 `sot/` 子目录下版本号最大的一个。
- **需要的文件**:
  - `*_opportunities.csv`:
    - 每只股票一对文件中的 “机会主表”:
      - `opportunity_id`
      - `stock_id`
      - `trigger_date`
      - `trigger_price`
      - `status`（`open` / `win` / `loss` 等）
      - `roi`（整体 ROI）
      - `completed_targets`（JSON 或辅助字段，可选）
      - 其他策略相关字段（例如标签、信号强度等）
  - `*_targets.csv`:
    - 每个机会的分段目标:
      - `opportunity_id`
      - `stock_id`
      - `date`（目标命中日期）
      - `price`（命中价格）
      - `sell_ratio`（本段卖出的仓位比例）
      - `roi`（该段的单段 ROI）
      - `reason`（止盈/止损/到期等）

> 注意: PriceFactorSimulator **不直接读取 K 线**，仅依赖枚举结果中的价格与日期。

#### 2.2 参数与配置

建议放在 `settings.py` 的 `simulator` 区域中:

- `simulator`:
  - `sot_version`: 使用的 SOT 版本号或 `"latest"`。
  - `start_date` / `end_date`: 模拟时间窗口（可为空，表示全量）。
  - `fees`: 交易成本配置（例如）:
    - `commission_rate`: 佣金率（双边）
    - `min_commission`: 最低佣金
    - `stamp_duty_rate`: 印花税率（卖出时）
    - `transfer_fee_rate`: 过户费（如需要）

#### 2.3 输出数据

- 目录: `app/userspace/strategies/{strategy_name}/results/simulations/{version_dir}/strategy_simulator/`
- 仅 JSON 输出（便于上层工具继续加工）:
  - `trades.json`:
    - 逐笔交易记录:
      - `date`
      - `stock_id`
      - `opportunity_id`
      - `side`（`buy`/`sell`）
      - `shares`
      - `price`
      - `amount`（含费用）
      - `fees_detail`
  - `summary_stock.json`:
    - 按 **单股** 汇总的统计:
      - `stock_id`
      - `opportunity_count_total`
      - `opportunity_count_participated`
      - `win_count` / `loss_count`
      - `total_pnl`
      - `avg_pnl_per_opportunity`
      - `max_drawdown`（基于该股“虚拟账户”）
      - 其他可选指标。
  - `summary_strategy.json`:
    - 策略整体视角:
      - 总机会数 / 参与机会数
      - 总收益 / 年化收益（基于模拟时间窗口）
      - 胜率 / 平均盈亏比
      - 最大回撤
      - 按行业/市值等维度的聚合（可选）
  - `settings_snapshot.json`:
    - 本次模拟的完整配置快照（方便复现）。

---

### 3. 核心业务规则（PriceFactorSimulator）

#### 3.1 单股视角的状态机

对每一只股票，Simulator 维护一套简化的 “账户状态”:

- `Position`:
  - `is_holding: bool`
  - `current_opportunity_id: Optional[str]`
  - `shares: int`（持有股数，初始 0）
  - `avg_cost: float`（含加仓摊薄）
  - `realized_pnl: float`（只用于统计）

> 无资金限制，**不维护现金**，仅统计 PnL。

#### 3.2 事件流构建

对单股:

1. 从 `opportunities.csv` 中选出属于该股的机会，按时间窗口过滤:
   - `trigger_date` ∈ `[start_date, end_date]`（如配置）
2. 从 `targets.csv` 中选出属于这些 `opportunity_id` 的所有目标记录。
3. 构建事件列表:
   - 每个机会:
     - 一个 “触发事件”:
       - `event_type = "trigger"`
       - `date = trigger_date`
       - `opportunity_id`
     - 若有 `completed_targets`:
       - 对每个分段:
         - `event_type = "target"`
         - `date = target.date`
         - 携带 `sell_ratio` / `price` / `roi` 等信息
4. 按 `date` 排序事件列表；
   - 同日多个事件时，按自然顺序（如 `(opportunity_id, event_type)`）排序。

#### 3.3 执行逻辑

##### 3.3.1 触发事件（买入）

当处理到某机会的 `trigger` 事件:

- 若 `position.is_holding == False`:
  - 以 `trigger_price`（考虑手续费）买入 **1 股**:
    - `shares = 1`
    - `avg_cost = fill_price`
    - `current_opportunity_id = opp_id`
    - `is_holding = True`
- 若 `position.is_holding == True`:
  - 默认: 跳过该机会（忽略新机会）
  - 除非 **用户加仓钩子** 主动调整（见 3.4）。

##### 3.3.2 目标事件（分段结算）

对于某个持仓中的 `current_opportunity_id`，处理该机会的 `target` 事件:

- 因 PriceFactorSimulator 不处理资金配比，推荐简化为:
  - 仍然尊重 `sell_ratio`，但在统计层面**以整个机会结果为主**：
    - 可以:
      - 记录分段收益（用于 future 扩展）
      - 当累计 `sell_ratio >= 1.0` 时，视为该机会完全结束:
        - 以最后一次目标价格作为整体平仓价，计算 1 股的整体 PnL:
          - `pnl = (last_target_price - avg_cost) * shares - fees_on_sell`
        - 更新 `realized_pnl += pnl`
        - 将 `position` 归零:
          - `shares = 0`
          - `is_holding = False`
          - `current_opportunity_id = None`
- 也可以直接基于枚举器计算好的总 `roi` 来计算 PnL:
  - `pnl = avg_cost * roi * shares`（再扣除卖出费用）

##### 3.3.3 T+1 规则（可选）

若需要更贴近真实交易:

- 买入:
  - 视作当日成交，不牵涉资金冻结（无资金约束）。
- 卖出:
  - 若 `target.date < trigger_date + 1 交易日`:
    - 可以选择将结算延迟到 `trigger_date + 1` 当日（对 PriceFactorSimulator 影响主要在统计时间点，可以简化处理）。

---

### 4. 钩子设计（加仓/干预）

为了允许用户扩展行为，提供若干钩子函数（在 userspace 策略中实现）:

- 示例签名（Python 伪代码）:

```python
def on_opportunity_event(
    stock_id: str,
    opportunity: Dict[str, Any],
    position: Dict[str, Any],
    event: Dict[str, Any],
) -> Dict[str, Any]:
    """
    在每个机会相关事件（trigger/target）调用一次。
    
    返回:
        {
            "action": "hold" | "close_and_enter_new" | "add_shares",
            "add_shares": int,  # 当 action == "add_shares" 有效
        }
    """
```

- 默认实现:
  - `action = "hold"`, `add_shares = 0`。
- 使用场景:
  - 用户可以在一个机会刚触发时，强制平掉旧机会并进场新机会。
  - 在目标事件时，用户根据自定义规则加仓/减仓。

Simulator 在执行核心逻辑后调用钩子，根据钩子返回内容调整 `Position` 状态。

---

### 5. 并发与调度

- PriceFactorSimulator 可以复用现有的多进程基础设施:
  - **作业粒度**: 每只股票一个 job。
  - 每个 Worker:
    - 读取该股对应的 `*_opportunities.csv` 和 `*_targets.csv`。
    - 运行上述单股事件循环。
    - 输出该股的交易记录和汇总到主进程（或写入各自临时文件，主进程再聚合）。
- 主进程:
  - 收集各 Worker 的结果，聚合为 `summary_strategy.json` 等。

---

### 6. 与 Capital Allocation Simulator 的关系

- PriceFactorSimulator 只回答: **“如果你每次发现价格因子机会都买 1 股，这个信号本身怎么样？”**
- 不考虑:
  - 资金是否足够
  - 多股票组合回撤控制
  - 同步资金轨迹
- Capital Allocation Simulator 在此之上引入资金和仓位约束，两者可以共享:
  - 机会/目标的解析逻辑
  - 交易成本模型
  - 钩子接口设计（可在更高层复用）。

