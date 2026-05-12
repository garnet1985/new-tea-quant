# 策略工作台设置 Schema（V1）

## 目标

为策略调试页提供前端可执行的字段模型（非 `core` 强模型 + `core` raw dict）。

---

## 总体规则

1. `core`：不走强模型，使用 raw dict 输入组件（Python dict/JSON 兼容）。
2. 非 `core`：走 schema 驱动表单。
3. 未暴露字段：保留原值，不在前端编辑。
4. `goal` 的 `protect_loss` / `dynamic_loss`：
   - 当对应 action 不再存在时，**直接删除对应配置块**。
5. `fees` 覆盖策略：
   - 默认显示全局 fees（只读）。
   - 勾选“覆盖全局费用”后，写入 section 内 `fees`。
   - 取消勾选时删除该 section 的 `fees` 块。

---

## 字段类型约定

- `text`：字符串输入
- `number`：数字输入（int/float）
- `switch`：布尔开关
- `select`：单选下拉
- `array_object`：对象数组（支持增删改）
- `raw_dict`：原始 dict 编辑器
- `readonly`：只读展示

---

## Section：Meta（只读 + 开关）

| fieldPath | displayNameZh | type | editable | 说明 |
|---|---|---|---|---|
| `name` | 策略名 | readonly | false | 只读展示 |
| `description` | 描述 | readonly | false | 只读展示 |
| `is_enabled` | 启用状态 | switch | true | 是否启用该策略 |

---

## Section：Core（用户自定义）

| fieldPath | displayNameZh | type | editable | 说明 |
|---|---|---|---|---|
| `core` | 核心参数 | raw_dict | true | 使用 Python dict/JSON 兼容编辑器 |

---

## Section：Goal

### 1) expiration

| fieldPath | displayNameZh | type | editable | 说明 |
|---|---|---|---|---|
| `goal.expiration.fixed_window_in_days` | 到期窗口天数 | number | true | 默认 30 |
| `goal.expiration.is_trading_days` | 按交易日计数 | switch | true | 默认 true |

### 2) stop_loss.stages（数组）

`fieldPath`: `goal.stop_loss.stages[]`

每项字段：

| fieldPath (item) | displayNameZh | type | editable | 说明 |
|---|---|---|---|---|
| `name` | 阶段名称 | text | true | 必填 |
| `ratio` | 触发比例 | number | true | 必填，止损通常为负数 |
| `close_invest` | 触发清仓 | switch | true | 与 `sell_ratio` 二选一 |
| `sell_ratio` | 卖出比例 | number | true | 可选，0~1 |

> 支持动态新增/删除 stage。

### 3) take_profit.stages（数组）

`fieldPath`: `goal.take_profit.stages[]`

每项字段：

| fieldPath (item) | displayNameZh | type | editable | 说明 |
|---|---|---|---|---|
| `name` | 阶段名称 | text | true | 必填 |
| `ratio` | 触发比例 | number | true | 必填，止盈通常为正数 |
| `close_invest` | 触发清仓 | switch | true | 与 `sell_ratio` 二选一 |
| `sell_ratio` | 卖出比例 | number | true | 可选，0~1 |
| `actions` | 触发动作 | select(multi) | true | 可选值：`set_protect_loss`、`set_dynamic_loss` |

> 支持动态新增/删除 stage。

### 4) protect_loss / dynamic_loss（自动块）

| fieldPath | displayNameZh | type | editable | 显示条件 |
|---|---|---|---|---|
| `goal.protect_loss.ratio` | 保本止损比例 | number | true | 任一 `take_profit.stages[].actions` 包含 `set_protect_loss` |
| `goal.protect_loss.close_invest` | 保本止损清仓 | switch | true | 同上 |
| `goal.dynamic_loss.ratio` | 动态止损比例 | number | true | 任一 `take_profit.stages[].actions` 包含 `set_dynamic_loss` |
| `goal.dynamic_loss.close_invest` | 动态止损清仓 | switch | true | 同上 |

> 若对应 action 全部删除，自动删除对应块。

---

## Section：Enumerator（仅最小暴露）

| fieldPath | displayNameZh | type | editable | 说明 |
|---|---|---|---|---|
| `enumerator.use_sampling` | 使用采样枚举 | switch | true | 控制全市场/采样股票池（与落盘路径无关） |

---

## Section：Price Simulator

### 基础字段

| fieldPath | displayNameZh | type | editable | 说明 |
|---|---|---|---|---|
| `price_simulator.use_sampling` | 使用采样版本 | switch | true | false=output，true=test |

### fees（可选覆盖）

UI 交互：
- 默认显示“全局费用（只读）”
- checkbox：`覆盖全局费用`
- 勾选后展示以下字段并写入 `price_simulator.fees`

| fieldPath | displayNameZh | type | editable |
|---|---|---|---|
| `price_simulator.fees.commission_rate` | 佣金率 | number | true |
| `price_simulator.fees.min_commission` | 最低佣金 | number | true |
| `price_simulator.fees.stamp_duty_rate` | 印花税率 | number | true |
| `price_simulator.fees.transfer_fee_rate` | 过户费率 | number | true |

取消勾选时删除 `price_simulator.fees`。

---

## Section：Capital Simulator

### 基础字段

| fieldPath | displayNameZh | type | editable | 说明 |
|---|---|---|---|---|
| `capital_simulator.use_sampling` | 使用采样版本 | switch | true | false=output，true=test |
| `capital_simulator.initial_capital` | 初始资金 | number | true | 默认 1_000_000 |

### allocation（按 mode 动态）

公共字段：

| fieldPath | displayNameZh | type | editable |
|---|---|---|---|
| `capital_simulator.allocation.mode` | 资金分配模式 | select | true |

`mode` 枚举值：
- `equal_capital`
- `equal_shares`
- `kelly`
- `custom`

动态字段：

| fieldPath | displayNameZh | type | 显示条件 |
|---|---|---|---|
| `capital_simulator.allocation.max_portfolio_size` | 最大持仓数 | number | `mode in [equal_capital, equal_shares, kelly, custom]` |
| `capital_simulator.allocation.max_weight_per_stock` | 单票最大权重 | number | `mode in [equal_capital, equal_shares, kelly, custom]` |
| `capital_simulator.allocation.lot_size` | 每手股数 | number | `mode == equal_shares` |
| `capital_simulator.allocation.lots_per_trade` | 每次手数 | number | `mode == equal_shares` |
| `capital_simulator.allocation.kelly_fraction` | Kelly 折扣系数 | number | `mode == kelly` |

### fees（可选覆盖）

UI 交互与 price_simulator 相同（checkbox 控制覆盖）：

| fieldPath | displayNameZh | type | editable |
|---|---|---|---|
| `capital_simulator.fees.commission_rate` | 佣金率 | number | true |
| `capital_simulator.fees.min_commission` | 最低佣金 | number | true |
| `capital_simulator.fees.stamp_duty_rate` | 印花税率 | number | true |
| `capital_simulator.fees.transfer_fee_rate` | 过户费率 | number | true |

取消勾选时删除 `capital_simulator.fees`。

---

## Section：Sampling

### 基础字段

| fieldPath | displayNameZh | type | editable | 说明 |
|---|---|---|---|---|
| `sampling.strategy` | 采样模式 | select | true | `uniform/stratified/random/continuous/pool/blacklist` |
| `sampling.sampling_amount` | 采样数量 | number | true | 默认 10 |

### 按模式动态字段

| fieldPath | displayNameZh | type | 显示条件 |
|---|---|---|---|
| `sampling.continuous.start_idx` | 连续采样起始索引 | number | `strategy == continuous` |
| `sampling.stratified.seed` | 分层采样随机种子 | number | `strategy == stratified` |
| `sampling.random.seed` | 随机采样随机种子 | number | `strategy == random` |
| `sampling.pool.stock_ids` | 股票池列表 | array(text) | `strategy == pool` |
| `sampling.pool.file` | 股票池文件路径 | text | `strategy == pool` |
| `sampling.blacklist.stock_ids` | 黑名单列表 | array(text) | `strategy == blacklist` |
| `sampling.blacklist.file` | 黑名单文件路径 | text | `strategy == blacklist` |

---

## 暂不在 V1 暴露

- `data`（先不进调试页主流程）
- `scanner`（先不进调试页主流程）
- 其余未列字段保持原样保留

---

## 与实现的衔接建议

1. 先按本文件生成前端 schema 常量（JS/TS）。
2. schema 渲染器只处理非 `core`。
3. `core` 复用现有 `pythonDictInputPanel`。
4. 保存前组装完整 settings：已编辑字段 + 未知字段原样保留。

