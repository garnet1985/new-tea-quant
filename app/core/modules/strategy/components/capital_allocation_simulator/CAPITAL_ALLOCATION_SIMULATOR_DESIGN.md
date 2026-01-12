## Capital Allocation Simulator 设计文档

### 1. 目标与定位

- **定位**: 在真实资金约束下，对枚举器 SOT 结果进行全市场回放的 **资金分配型模拟器**。
- **核心思想**:
  - 基于 SOT 版本中的所有机会与目标，按时间轴回放。
  - 维护一套全局账户（现金 + 持仓），对每个新机会决定是否、以多大仓位参与。
  - 支持多种资金分配策略:
    - 等资金投入（equal capital）
    - 等股投入（equal shares）
    - 凯莉公式（Kelly-based allocation，带保守因子）
- **典型用途**:
  - 在**真实资金限制**下评估策略全局表现:
    - 总收益 / 收益曲线 / 最大回撤
    - 资金使用效率
    - 多股票组合层面的风险收益特征。

---

### 2. 输入与输出

#### 2.1 输入数据

- **来源**: `results/opportunity_enums/sot/{version_dir}/`
- **版本选择**:
  - 在 `settings.simulator.sot_version` 中显式配置:
    - 具体版本号: 如 `"1_20260112_161317"`，若该目录不存在则 **拒绝执行**。
    - `"latest"`: 选择 `sot/` 子目录下版本号最大的一个。
- **需要的文件**:
  - `*_opportunities.csv`（所有股票）:
    - 字段示例:
      - `opportunity_id`
      - `stock_id`
      - `trigger_date`
      - `trigger_price`
      - `status`（`open` / `win` / `loss` 等）
      - `roi`（整体 ROI）
      - 其他策略字段
  - `*_targets.csv`:
    - 字段示例:
      - `opportunity_id`
      - `stock_id`
      - `date`
      - `price`
      - `sell_ratio`
      - `roi`
      - `reason`

> 注意: 与 Strategy Simulator 一样，本模拟器 **不再重新读取 K 线**，一切基于枚举结果中的价格和日期。

#### 2.2 参数与配置

建议在 `settings.py` 的 `simulator` 块中配置:

- `simulator`:
  - `sot_version`: 使用的 SOT 版本号或 `"latest"`。
  - `start_date` / `end_date`: 模拟时间窗口（可为空，表示用 SOT 数据的最早/最晚日期）。
  - `initial_cash`: 初始总资金（如 `1_000_000`）。
  - `allocation_mode`: 资金分配模式:
    - `"equal_capital"`: 等资金投入
    - `"equal_shares"`: 等股投入
    - `"kelly"`: 凯莉公式（默认）
  - `equal_capital` 配置:
    - `per_trade_capital`: 每次机会尝试投入的资金，例如 `10000`。
  - `equal_shares` 配置:
    - `per_trade_shares`: 每次机会尝试买入的股数，例如 `500`。
  - `kelly` 配置:
    - `kelly_divisor`: 凯莉比例的保守除数，默认 `5`（即 `f_effective = f_raw / 5`）。
  - 交易成本 `fees`:
    - `commission_rate`
    - `min_commission`
    - `stamp_duty_rate`
    - `transfer_fee_rate`

#### 2.3 输出数据

- 目录: `app/userspace/strategies/{strategy_name}/results/simulations/{version_dir}/capital_allocation/`
- 仅 JSON 输出:
  - `trades.json`:
    - 逐笔交易:
      - `date`
      - `stock_id`
      - `opportunity_id`
      - `side`（`buy`/`sell`）
      - `shares`
      - `price`
      - `amount`（不含费用）
      - `fees_detail`
      - `cash_after_trade`
      - `equity_after_trade`
  - `portfolio_timeseries.json`:
    - 按交易日的账户/组合快照:
      - `date`
      - `cash`
      - `equity`（总资产 = 现金 + Σ持仓市值）
      - `positions_snapshot`（可选简化版: 持仓数量、按市值 TopN）
  - `summary_stock.json`:
    - 按单股聚合:
      - `stock_id`
      - `trade_count`
      - `total_pnl`
      - `win_trades` / `loss_trades`
      - `max_position_shares`
      - `max_drawdown_stock_level`（可选）
  - `summary_strategy.json`:
    - 策略级别：
      - `initial_cash`
      - `final_cash`
      - `final_equity`
      - `total_return`
      - `annualized_return`（基于模拟窗口）
      - `max_drawdown`
      - `win_rate_by_opportunity`
      - `win_rate_by_trade`
      - 资金使用率、平均仓位等。
  - `settings_snapshot.json`:
    - 本次 Capital Allocation 模拟的配置快照。

---

### 3. 账户与持仓模型

#### 3.1 Account 结构

全局只有一个账户对象:

- `Account`:
  - `initial_cash: float`
  - `cash: float`  — 当前可用现金
  - `positions: Dict[stock_id, Position]`
  - `equity: float` — 当前总资产估值
  - `history`: 可选，用于记录每日/每事件后的快照。

#### 3.2 Position 结构

每只股票的持仓:

- `Position`:
  - `stock_id: str`
  - `shares: int`
  - `avg_cost: float`  — 含交易成本摊薄
  - `realized_pnl: float`
  - `current_opportunity_id: Optional[str]` — 当前持仓对应的机会 ID（若为 `None` 则不绑定机会）

> 规则: 默认情况下，同一时刻一只股票只能有一笔“主体持仓”，即 **一个活跃机会**。  
> 新机会出现时，若已有持仓，则默认不再开新仓（除非钩子干预）。

---

### 4. 事件流与时间轴

#### 4.1 事件构建

从 SOT 结果构建全局事件流:

1. 遍历所有 `*_opportunities.csv` 和 `*_targets.csv`:
   - 按 `settings.simulator.start_date / end_date` 筛选机会:
     - `trigger_date` ∈ `[start_date, end_date]`（若 start/end 不配置，则用全量）。
2. 对每个机会构建事件:
   - 开仓事件:
     - `event_type = "trigger"`
     - `date = trigger_date`
     - 其他字段: `opportunity_id`, `stock_id`, `trigger_price` 等。
   - 分段目标事件:
     - 对 `targets` 表中该机会的每一条记录:
       - `event_type = "target"`
       - `date = target.date`
       - 携带 `sell_ratio`, `price`, `reason` 等。
3. 合并成全局事件列表:
   - 按 `date` 升序排序。
   - 同日多事件: 按自然顺序（如 `(stock_id, opportunity_id, event_type)`）排序。

#### 4.2 执行主循环（单进程）

Capital Allocation Simulator 为了保证资金一致性，采用 **单进程主循环**:

```python
for event in events:
    update_account_valuation_if_needed(event.date)
    if event.type == "trigger":
        handle_trigger_event(event, account)
    elif event.type == "target":
        handle_target_event(event, account)
```

- `update_account_valuation_if_needed(date)`:
  - 若按日需要输出 `portfolio_timeseries`，则在每一“新日期”计算一次 `equity`。
  - 持仓市值估值可使用:
    - 机会触发价 / 目标价作为该日“有效价”，或
    - 未来可扩展为从 K 线拉取收盘价（当前阶段可以用简化模型）。

---

### 5. 资金分配规则

#### 5.1 等资金投入（`allocation_mode = "equal_capital"`）

- 配置:
  - `per_trade_capital = 10000`（例）
- 对某触发事件:
  1. 若该股已有持仓（`shares > 0`）:
     - 默认 **跳过该机会**（除非钩子指示先平仓再开仓）。
  2. 检查现金:
     - 若 `cash < per_trade_capital` → **跳过机会**。
  3. 计算最大可买股数（中国 100 股一手）:
     - `P = trigger_price`
     - `max_shares = floor(per_trade_capital / P)`
     - `lots = max_shares // 100`
     - `buy_shares = lots * 100`
     - 若 `buy_shares == 0` → **跳过机会**。
  4. 计算实际成本与费用:
     - `gross_amount = buy_shares * P`
     - 计算费用 `fees = calc_fees(gross_amount, side="buy")`
     - `total_cost = gross_amount + fees`
     - 若 `cash < total_cost`（极端情况）→ 回退（可选择跳过该机会）。
  5. 执行买入:
     - `cash -= total_cost`
     - 新建/更新 `Position`:
       - `shares = buy_shares`
       - `avg_cost = total_cost / buy_shares`
       - `current_opportunity_id = opportunity_id`

#### 5.2 等股投入（`allocation_mode = "equal_shares"`）

- 配置:
  - `per_trade_shares = 500`（例）
- 对某触发事件:
  1. 若该股已有持仓 → 默认跳过。
  2. 目标股数 = `N = per_trade_shares`（可要求是 100 的倍数）。
  3. 计算成本:
     - `gross_amount = N * P`
     - `fees = calc_fees(gross_amount, "buy")`
     - `total_cost = gross_amount + fees`
     - 若 `cash < total_cost` → **跳过机会**。
  4. 执行买入，更新 `cash` 与 `Position`。

#### 5.3 凯莉公式（`allocation_mode = "kelly"`，默认）

##### 5.3.1 胜率 `p` 的计算

在**当前事件日 D**，回测起始日 `S` 下:

1. 从 SOT 结果中筛选出所有**完整机会**:
   - `trigger_date >= S`
   - `sell_date < D`（机会已结束）
   - `status != 'open'`
2. 统计:
   - `total = 完整机会数量`
   - `win_count = ROI > 0 的机会数量`
3. 若 `total == 0`:
   - `p = 0.5`（默认 50% 胜率）
4. 否则:
   - `p = win_count / total`

##### 5.3.2 仓位比例 `f` 的计算（简化版凯莉）

标准凯莉公式需要赔率 `b`，但当前需求中并未显式定义 `b`。  
为避免引入额外参数，采用 **简化形式**:

- `f_raw = 2 * p - 1`
  - 若 `p = 0.5` → `f_raw = 0`
  - 若 `p > 0.5` → 正值，胜率越高 `f_raw` 越大。
  - 若 `p < 0.5` → 负值，表示应减少或停止投入。
- 保守控制:
  - 使用 `kelly_divisor = k`（默认 `5`）:
  - `f = max(0, f_raw) / k`
    - 若 `p <= 0.5` → `f = 0`（不参与）
    - 否则 `0 < f <= 1/k`。

##### 5.3.3 实际买入逻辑

对某触发事件:

1. 若该股已有持仓 → 默认跳过。
2. 计算当前 `p` 和 `f`:
   - 若 `f == 0` → 跳过机会。
3. 目标资金:
   - `target_capital = f * cash`
4. 按一手取整:
   - `max_shares = floor(target_capital / P)`
   - `lots = max_shares // 100`
   - `buy_shares = lots * 100`
5. 若 `buy_shares == 0` 或 `cash` 不足以支付 `buy_shares * P + fees` → 跳过机会。
6. 否则执行买入，如前述等资金模式。

---

### 6. 机会结束与资金释放（T+1 规则）

在处理 `target` 事件时:

- 对某持仓中的机会，其 `targets` 表中的每一条记录代表一段平仓:
  - 每个分段结果只要满足:
    - `target_date >= trigger_date + 1 交易日`
  - 即可在该 `target_date` 当日:
    - 计算分段的卖出金额与费用:
      - `sell_amount = shares_sold * target_price`
      - `fees = calc_fees(sell_amount, "sell")`
    - 立刻将净收益 `sell_amount - fees - 对应成本` 计入 `cash`。
- 多段止盈/止损:
  - 多个 `sell_ratio` 累加到 `1.0` 视为 **完全平仓**。
  - Position 中 `shares` 减少对应的数量，直到归零。

> 对于 `< T+1` 的边界情况，可用日期工具封装“是否已跨 T+1”的判断逻辑。

---

### 7. 多股票、多机会冲突处理

#### 7.1 同股票多机会

- 若 `positions[stock_id].shares > 0`:
  - 新机会默认 **不再开仓**。
  - 除非用户钩子显式指示:
    - “先平掉当前仓位，再开新机会” 或
    - “在当前机会基础上加仓”（更复杂场景）。

#### 7.2 多股票并发机会

- 在同一交易日、多个股票迎来触发事件时:
  - 按事件流构建时的 **自然顺序**:
    - 可按 `(date, stock_id, opportunity_id)` 排序。
  - 资金不足时:
    - 谁先被处理、且资金足够，就有机会开仓；
    - 后续机会若资金不足则自动被跳过。

---

### 8. 钩子设计（可选扩展）

为了支持用户高级资金管理策略，可提供钩子接口:

- 示例:

```python
def before_open_position(
    opportunity: Dict[str, Any],
    account: Dict[str, Any],
    suggested_shares: int,
) -> Dict[str, Any]:
    """
    在开仓前调用，允许用户调整开仓动作:
    返回:
        {
            "allow": bool,          # 是否允许开仓
            "shares": int | None,   # 如指定则覆盖 suggested_shares
        }
    """
```

```python
def before_close_position(
    opportunity: Dict[str, Any],
    target: Dict[str, Any],
    account: Dict[str, Any],
    position: Dict[str, Any],
) -> Dict[str, Any]:
    """
    在分段平仓前调用，允许用户调整平仓动作。
    """
```

- 默认实现:
  - `allow = True`，不更改 shares。

---

### 9. 并发模型

- **Capital Allocation Simulator 必须主逻辑单进程**:
  - 因为需要维护一套全局资金与持仓状态，事件必须按照统一时间轴串行处理。
- 可以考虑的优化:
  - 一些静态分析（如预计算机会胜率）可提前并行完成，然后在主循环中直接使用。
  - 但核心事件处理（开仓/平仓/更新账户）保持单线程。

---

### 10. 与 Strategy Simulator 的关系

- 两者都:
  - 基于同一套 **SOT 枚举结果**。
  - 使用相同的交易成本模型、日期工具和机会/目标解析逻辑。
  - 可以共用部分代码（如事件流构建）。
- 不同点:
  - Strategy Simulator:
    - 每股独立、无资金约束，可多进程。
    - 关注的是“信号质量”。
  - Capital Allocation Simulator:
    - 有一套全局账户状态，必须单进程。
    - 关注的是“在真实资金约束下的组合表现”。

