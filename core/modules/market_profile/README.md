# Market Profile 模块设计

> 状态：加载 / parse / 对外 API 已实现；已与 strategy 枚举标注、price_sim / capital 成交过滤集成。配置发现与合并委托 `core.infra.project_context.DiscoveryManager`。

## 1. 目标与边界

### 1.1 职责

- 加载并合并 **市场制度配置**（涨跌幅比例、最小申报单位等）。
- 按 `stock_id` 解析出可查询的规则结果，供回测 / 资金模拟等模块调用。

### 1.2 不负责（属于策略回测 / `simulation`）

- 涨跌停日 **是否仍允许成交**（`simulation.edges.allow_buy_at_limit_up` / `allow_sell_at_limit_down`）——在 **price_sim / capital** 执行，不在本模块内决定默认值。
- 滑点、`buy_price_model` / `sell_price_model`、费率（`fees`）。
- 信号、仓位、止盈止损（`goal`）。

### 1.3 与配置分层

| 层级 | 位置 | 内容 |
|------|------|------|
| 市场 Profile | `core/default_config/markets/*.json` + `userspace/config/markets/*.json` | 制度事实：涨跌幅、lot |
| 策略 Settings | `userspace/strategies/<name>/settings.py` | `market_profile` 选市场；`simulation` 等回测假设 |

**涨跌停拆分**

- **Profile**：`ratio` + `matching` → 计算 `limit_up` / `limit_down`。
- **Enumerator**：在机会 / 目标行上 **标注** `buy_at_limit_up`、`sell_at_limit_down` 等，**不删除**机会（保留策略信号完整性）。
- **Simulation.edges**：`allow_buy_at_limit_up` / `allow_sell_at_limit_down`（默认 `true`）在 **price_sim、capital** 读取标注后决定是否跳过该笔买卖。

---

## 2. 配置文件

### 2.1 路径

- 默认：`core/default_config/markets/{profile_id}.json`（如 `china_a_stock.json`）。
- 用户覆盖：`userspace/config/markets/{profile_id}.json`（同名文件）。

### 2.2 Profile 发现

- 对两个 `markets/` 目录扫描 `*.json`，取 **文件名（无后缀）并集** 作为 `profile_id` 列表。
- MVP 默认 profile：`china_a_stock`（见 `constants.DEFAULT_PROFILE_ID`）。

### 2.3 合并策略（按文件）

1. 以 core 文件为底，userspace 同名文件覆盖。
2. **标量 / `default_*`**：userspace 字段覆盖 core。
3. **`rules.<rule_type>.rules[]` 数组**：按条目 **`key`** 合并（同 `key` 用户条目覆盖 core；用户新增 `key` 追加；未提及的 core 条目保留）。
4. 禁止「用户只写一条 rule 却丢掉 core 其余条目」：先合并 `default_*` 与块级标量，再对数组做 by-`key` merge。

### 2.4 JSON 形状（示例）

见 `core/default_config/markets/china_a_stock.json`。

- 顶层：`name`、`description`、`rules`。
- `rules` 一级 key 对应一个 **Rule Engine**（如 `amplitude_limit`、`lot_size`）。
- 条目中 `matching.id.start_with`：对 `stock_id` **点号前数字码**匹配；多条前缀默认 **OR**。

---

## 3. 策略如何选择市场

- Settings 根级字段：**`market_profile`**（与模块名一致）。
- 选填；缺省 `china_a_stock`。
- 示例：`setup/init_userspace/userspace/strategies/settings_example.py`。
- **校验与加载**：`StrategyMarketProfileSettings`（`strategy_settings`）校验 `profile_id` 是否存在；运行时经 `get_market_profile(profile_id)` 加载。

---

## 4. 模块结构

```text
core/modules/market_profile/
├── README.md                      # 本文档
├── module_info.yaml
├── constants.py                   # DEFAULT_PROFILE_ID、MARKETS_CONFIG_DIR
├── profile.py                     # MarketProfile 聚合（类似 StrategySettings）
├── market_profile_manager.py      # 对外入口、缓存、registry 调度
├── __init__.py
├── rule_engines/
│   ├── __init__.py                # REGISTRY：Engine 类列表
│   ├── shared/
│   │   ├── base.py                # MarketRuleEngineBase, CompiledRuleBase
│   │   └── matching.py            # id.start_with 等
│   ├── amplitude_limit/
│   │   ├── parser.py              # AmplitudeLimitEngine
│   │   ├── models.py
│   │   └── helper.py              # 限价舍入等（可选）
│   └── lot_size/
│       ├── parser.py
│       ├── models.py
│       └── helper.py
└── __test__/                      # 实现阶段补充
```

---

## 5. 核心类型与流程

### 5.1 加载流程

```text
get_market_profile(profile_id?)
  → DiscoveryManager.load_overridable_config(MARKETS_CONFIG_DIR, profile_id, merge_fn=...)
  → MarketProfile.from_raw(profile_id, raw)
       → 遍历 REGISTRY 中各 Engine
       → block = raw["rules"].get(engine.rule_key)
       → 无 block：跳过；有 block：compiled = engine.parse(block)
       → 未知 rules key（不在 REGISTRY）：logging.warning，整段忽略
  → MarketProfile(profile_id, compiled_map, meta...)
```

### 5.2 Rule Engine 契约

**`MarketRuleEngineBase`**（`rule_engines/shared/base.py`）

- 类属性 `rule_key: str` — 对应 JSON `rules` 下一级 key。
- `parse(block: dict) -> CompiledRuleBase` — 启动时执行一次。

**`CompiledRuleBase`**

- `resolve(stock_id: str)` — 子类返回具体类型（ratio、lot、限价等）。

**Resolve 顺序**（各 engine 一致）

1. 使用 `default_*`。
2. 扫描例外列表；**第一条命中的 matcher 生效**（编译时可按前缀长度降序排列，避免歧义）。

### 5.3 已注册 Engine（MVP）

| `rule_key` | 目录 | 输出（resolve） |
|------------|------|-----------------|
| `amplitude_limit` | `rule_engines/amplitude_limit/` | `limit_ratio`；`compute_limit_prices(prev_close, status_tags?)`；可选 `default_risk` / `rules[].risk`（`st` / `star_st` 覆盖比例） |
| `lot_size` | `rule_engines/lot_size/` | `min_lot`、`lot_step`；`floor_buy_quantity` |

新增 rule：新增子包 + 在 `rule_engines/__init__.py` 的 `REGISTRY` 注册；未知 key 不注册即忽略。

### 5.4 `MarketProfile` 聚合

- 持有 `profile_id`、`name`、`description`。
- 持有 `Dict[str, CompiledRuleBase]` 或显式属性（`amplitude_limit`、`lot_size`）。
- 对外 typed 方法（供 simulator 使用）：
  - `resolve_limit_ratio(stock_id, status_tags=None)`
  - `compute_limit_prices(stock_id, prev_close, status_tags=None) -> (up, down)`
  - `resolve_lot_rules(stock_id)`
  - `floor_buy_quantity(shares, stock_id)`（可选）
- 可选：`get_compiled(rule_key)` 用于调试。

### 5.5 `MarketProfileManager`

- `get_profile(profile_id: Optional[str] = None) -> MarketProfile` — 带模块级缓存。
- 薄封装上述 resolve API，或调用方直接拿 `MarketProfile`。

---

## 6. 依赖与 project_context

- **配置发现 / 可覆盖加载**：`core.infra.project_context.DiscoveryManager`
  - `discover_configs("markets")`
  - `load_overridable_config("markets", profile_id, merge_fn=merge_market_profile_dicts)`
- **market 专用合并策略**：`core.infra.project_context.config_merge_policies.merge_market_profile_dicts`
- **本模块**：`constants.MARKETS_CONFIG_DIR`（`"markets"`），配置 IO 不重复实现。
- **禁止**：依赖 `modules.strategy`（避免环依赖）。

---

## 7. 调用方

| 调用方 | 用法 |
|--------|------|
| Enumerator | `stamp_buy_tradability` / `stamp_target_tradability`；CSV 含 `buy_at_limit_up`、`sell_at_limit_down`、`stock_status_at_trigger`（供价/资 `skip_investment_when`） |
| Price factor | `allow_*_at_limit_*` 过滤投资与目标；读 CSV 标注或 `buy_prev_close` 重算 |
| Capital allocation | `resolve_lot_rules`、`floor_buy_quantity`；`allow_*` / `skip_trade_when_insufficient` |
| Strategy 入口 | `settings["market_profile"]` → `get_market_profile(...)` |
| Scanner | 信号日触及涨停时标注 `buy_at_limit_up` 与 `metadata.tradability_hint`，不过滤机会 |

---

## 8. 测试计划（实现时）

- `matching`：`000001.SZ`、`688981.SH`、北交所 OR 前缀。
- `DiscoveryManager`：userspace 按 `key` 覆盖一条 rule。
- Engine：未知 `rules` 顶层 key 被忽略。
- `MarketProfile`：主板 10%、科创 20%、lot 200/1。

---

## 9. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-05 | 初版设计；配置迁至 `default_config/markets/`；模块骨架占位 |
