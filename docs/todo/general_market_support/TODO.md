# General Market Support — Todo

> **目标市场（权益）：** A 股、美股、港股（期权/期货另轨）。  
> **三步路线：** ① 交易规则收进 MP → ② 扩展 MP 可交易性给美/港 → ③ 日历与循环支持日以下 + 可覆写撮合。

## 北极星（框架职责）

**框架只做通用能力：** 你给我一组数据 + 一套交易规则，我按规则回测。

| 层 | 知道什么 | 不知道什么 |
|----|----------|------------|
| **strategy / BE / data_contract（读侧）** | 时间序列、标的集合、规则接口（手数/T+N/费用/日历 id/撮合…） | A 股 / 港股 / 美股；哪家 vendor |
| **market_profile** | 某市场的**规则实现**（可插拔） | 行情从哪来 |
| **userspace data pack** | 具体数据怎么拉、怎么落表 | 回测怎么撮合 |

验收口径：core 路径里不应再出现 `if china_a` / 写死 `SSE` / 印花税默认 / ST 词表；这些都从「注入的规则 + 注入的数据」来。市场差异 = 换 pack + 换 profile，不是换引擎。

### 对数据的薄硬约定（只有引擎自己啃的才定 schema）

判据：**core（strategy/BE）是否按字段名消费**。是 → 固定 schema；否、只 forward 给钩子 → 结构可松散甚至完全不同。

**必须定 schema（就这三类）：**

| 数据 | 为何必须同名同形 |
|------|------------------|
| **股票列表** | 引擎里有选股/过滤股票池；filter 认固定字段与维度 |
| **股票分类**（行业等维表/映射） | 同上，过滤函数按分类字段筛池 |
| **股票 K 线** | Timeline 推进；止盈止损/成交读 `open/high/low/close`（及常用 `vol`/`pre_close`）等固定名 |

**不必定死 schema：** LPR、公司财务、资金流、宏观、自定义 required 等——管线只是加载后 **转发给** `is_opportunity` 等钩子，策略自己解释形状；换市场可以完全不同。

**附带：** 交易日历仍被 BE 当开市日序列用，属于时钟基础设施（和「过滤/撮合字段」不是同一类，但多市场时 `market` + 开市标记仍要稳定）。ST 等市场扩展继续勿写进 core 必选自动注入。

## 三步路线（在北极星下重述）

三步 **不用换、也不用重排**；变的是动机：不是「给引擎加港美功能」，而是「让 core 只吃数据+规则」。港/美 = 第一批证明用的 pack + profile。

| 步 | 还做什么 | 北极星下的含义 / 验收 |
|----|----------|----------------------|
| **1** | 规则收进 MP；strategy/BE（及读路径默认）去市场硬编码 | core **不认识** A/港/美；只调规则接口。A 股用现有 pack+profile 零回归；换 us/hk profile 时不再误用 SSE/印花税/ST |
| **2** | 扩展可交易性 API 表面 | 不是「为港美改引擎」，而是 **规则接口够表达** 常见股票制度；港/美 pack 能实现这些接口。探针 = 缺哪条规则就补哪条 API |
| **3** | 亚日时钟 + 状态带交易日；撮合可覆写 | 引擎只认 **bar 序列 + FillMatcher + 规则**；日线是 interval=1d 特例。分钟数据仍由 pack 提供 |

**不必改成的事：** 不把「做港美数据 pack」并进三步（仍是 userspace）；不把 UI/Agent 并进三步；不因北极星去先做衍生品。

**会多盯一点的（仍属 1～2，不是新大步）：** data_contract / resolver **读侧**也不该写死 A 股（如强制 `qfq`、自动注入 `st_periods`）——应随 profile/pack 声明，否则「通用引擎」名不副实。

## 结论（第一步焦点）

先让 core 只依赖 **注入的规则**；可交易性接口进 MP。港/美日线切换是验收手段，不是目的本身。

---

## 可交易性 API 盘点（相对 A / 美 / 港）

图例：✅ 已有 · ❌ 缺失（应收进 MP）· △ 有一部分 / stub 不准 · — 该市场不适用或可简化

### A. 已有（`MarketBaseRules`）

| API 能力 | A 股 | 美股 | 港股 | 说明 |
|----------|:----:|:----:|:----:|------|
| 涨跌幅 / 涨跌停价 / 贴板判断 | ✅ | ✅（ratio=0 关闭） | ✅（关闭） | 美/港用「无涨跌停」覆写即可 |
| 手数 min/step、按票 matching | ✅ | ✅（1 股） | △ | 港股真实是**每股不同 board lot**，现 stub 写死 100，不够 |
| 卖出零股一次清完 | ✅ | ✅ | △ | 同上，依赖 lot 解析 |
| T+N / `is_allowed_to_sell` | ✅ T+1 | △ stub=T+0 | △ stub=T+0 | 现金股常见美 T+1、港 T+2；stub 偏「回测当日可卖」需产品定 |
| `pnl_polarity` | ✅ cn | ✅ intl | ✅ intl | UI |

### B. 第一步必补（硬编码在 strategy/BE，挡住切 profile）

| 缺失 API（建议名，可改） | A 股 | 美股 | 港股 | 现状 |
|--------------------------|:----:|:----:|:----:|------|
| `calendar_market_id()` | SSE | NYSE/NASDAQ 日历源 | HKEX | 调用方写死 `SSE` |
| `fee_defaults()` / fee schema | 佣金+最低+印花税卖出+过户 | 佣金 / SEC 等（无 A 股印花税） | 佣金+印花税+交易费等 | `FeeCalculator` A 股默认 |
| `risk_free_key()` | SHIBOR | SOFR/T-bill 等 | HIBOR 等 | 写死 SHIBOR |
| `trading_days_per_year()` | 242～252 | ~252 | ~247 | 写死 `252` |
| `known_risk_tags()` | `st` / `star_st` | 空或另套 | 空或另套 | risk_control 写死 ST |
| 引擎勿偷默认 `china_a_stock` 分支 | ✅ | ✅ | ✅ | 多处 fallback |

日线成交（`next_open` 等）三市可先共用；**第一步不扩 fill API**。

### C. 第二步候选（权益日线「跑得可信」时再按探针扩）

| 缺失 / 不足 API | A 股 | 美股 | 港股 | 为何可能需要 |
|-----------------|:----:|:----:|:----:|-------------|
| `currency()` | CNY | USD | HKD | 费用地板、报表单位、多市场组合前置 |
| `tick_size(price)` / 价位表 | 通常 0.01 | 通常 0.01 | **按价格带跳档** | 港股申报价；影响限价/涨跌停价取整 |
| 每股 board lot 解析（数据驱动） | 前缀规则够用 | 1 股 | **每票不同手数** | 现 lot matching 不够表达港股 |
| `short_selling_allowed` / 持仓方向 | 融券受限，现偏多头 | 常允许 | 常允许 | 不做空则美/港策略空间被砍 |
| 停牌 / 不可交易状态 | 有 ST 等，停牌多在数据层 | halt | halt/停牌 | 可交易性门闸；可与 risk tags 合流 |
| 涨跌停可否成交（策略里已有开关） | 重要 | — | — | 宜升到 MP 默认 + 策略可覆写 |
| 交收 T+N 与「日历日 vs 交易日」语义 | 交易日 | 定准 T+1 | 定准 T+2 | stub 与真实制度对齐 |
| 最低成交金额 / 申报约束 | 少用 | 少用 | 偶发 | 低优先级 |

不做开放式「全世界规则」；用 1～2 个美/港日线回测当探针，上表有痛再实现。

### D. 期权 / 期货？（目标先放入、实现另轨）

现有 `commodity_future` stub **只有** 涨跌幅前缀 + 1 手，**远不够**。期权无 profile。

衍生品相对权益 **多出来、且不能硬塞进当前股票 API** 的典型能力：

| 能力 | 期货 | 期权 | 建议 |
|------|:----:|:----:|------|
| 合约乘数 / 合约规模 | 需要 | 需要 | 新 API 族，勿复用 `lot` 语义硬撑 |
| 保证金 / 盯市 | 需要 | 需要 | 组合引擎另一条路径 |
| 到期日 / 行权 / 交割 | 需要 | 需要 | |
| 主力连续 / 换月 | 需要 | — | 数据+规则 |
| 权利金 vs 期货价格 | — | 需要 | |
| 夜盘 session | 常见 | 视品种 | 偏日历/session，接近分钟议题 |

**建议：** 目标文档里承认「未来要覆盖期权期货」，但 **第一步～第二步只闭环 A/美/港股票日线**；衍生品开独立 todo（例如 `docs/todo/derivatives_market_support/`），避免把 `MarketBaseRules` 股票接口撑变形。

---

## 第一步 Todo

- [ ] **定第一步可交易性 API**（上表 B）：日历、费用、RF/年化、风险标签  
- [ ] **填齐 profile**：`china_a_stock` 零回归；`us_stock` / `hong_kong` 补全 B  
- [ ] **改 strategy / BE 调用方**：去 SSE / 印花税默认 / SHIBOR·252 / ST whitelist 硬编码  
- [ ] **A 股日线零回归**；切 us/hk 时规则路径正确（可无真实行情）

## 验收（第一步）

1. A 股日线行为与改前一致。  
2. 只切 `market_profile`，日历 id / 费用 / RF / 风险标签跟随，无市场 if。

## 第二步 Todo（第一步后）

- [ ] 按美/港日线探针，按需实现上表 C（currency、tick、board lot、做空、停牌、T+N 对齐等）  
- 期权期货不进本步。

---

## 第三步：如何变成小于日线交易？

**一句话：循环仍按 bar/tick 走；状态里要能拿到「当前交易日」**（以及开市日序列），T+N / 持有天数按日算，不要按分钟点数算。

不是双层循环。日线时 point 本身就是日；分钟时 point 是分钟，但 context/investment 状态要带 `trade_date`（或等价字段）。

今天的坑：很多地方把 timeline points 直接当「开市日列表」用；升到分钟后会把「持有 2 个交易日」数成几百根分钟。

### 3.1 要改什么

**1) Session / 日历（生成两轴）**

- MP 或 Calendar 侧提供 session 模板（开收盘、午休；半日市）。
- 由 session + bar 周期（1m/5m…）生成 **tick 点列**；开市日列表仍走现有 `load_open_dates`。
- 关键：`calendar_service.py`、`market_profile` session 面、`Timeline.from_calendar_window` 旁增 `from_session_bars`（或等价）。

**2) BE Timeline 循环**

- `drive` / `on_tick(ctx, point, index)` **可保留**——循环本身与点粒度无关。
- 改的是 **points 内容**（分钟戳）与 consumers 解释；`kind=clock` 真正用起来。
- Slice 窗口不能再按「分钟点数」当「交易日数」切块（内存会爆）→ 按交易日或时间跨度切。
- 关键：`backtest_engine/core/timeline/timeline.py`、`schedule/slice_based/*`。

**3) 可覆写撮合 `FillMatcher`（你说的可复写函数）**

- 现状：成交写死在 `Investment._resolve_entry_price` / `_resolve_exit_price`（`next_open` / `touch` / OHLC…）。
- MP 里的 `MatchingService` 是 **标的 ID 前缀匹配**，不是订单撮合——**不要复用这名字做 fill**。
- 抽出协议，例如：`can_enter` / `enter_price` / `can_exit` / `exit_price` / `defer_to_next_tick`；默认实现 = 现有日线逻辑。
- 策略或 MP 可挂自定义 matcher；`next_open` 在亚日下 = **下一根 timeline bar 的 open**，不是「下一自然交易日」（除非轴仍是日）。
- 滑点 / 涨跌停门闸 / 流动性可留在 matcher 之后（现有链路）。
- 关键：`investment/investment.py`、`tradability.py` 配置挂载点。

**4) 数据面（第三步配套，否则无 bar 可跑）**

- K 线 PK 今日 `(id, term, date)` 且 `date` 仅 8 位 → 需 bar 时间（datetime 或更长戳）+ `term=1min` 等。
- Contract 增加分钟 key；`AsOfSlice` 按时间戳对齐，不再只比 `YYYYMMDD`。
- 关键：`stock_klines/schema.py`、`data_keys.py`、`as_of_slice.py`。

**5) Strategy 语义对齐**

- T+N / holding / pending_wait：**只数交易日轴**，从 tick 映射出 `trade_date` 再算。
- 退市、到期等按交易日，勿用分钟字符串直接比。
- 止盈止损按每根 bar 的 high/low 自然扩展。

**6) 组合日报（可先不动）**

- 日终 MTM + √252 可继续按 **交易日** 出账户报表；不必第一步就做分钟权益曲线。
- 若以后要日内权益，另开 `periods_per_year`（跟 bar 频率），勿把分钟收益直接 √252。

### 3.2 什么可以先不动

- BE `TickFn` / `drive` 调度壳、InvestmentTracker「先出后进再开」顺序。
- MP 的 lot / 涨跌停 / T+N **API 形状**（输入改为交易日计数即可）。
- 日线作为 `bar_interval=1d` 的特例：同一套 Timeline + 默认 FillMatcher，回归路径清晰。

### 3.3 第三步 Todo（草稿，实施前再拆）

- [ ] Session 规格 + 由 session 生成 tick 轴；交易日轴与 tick 轴拆开传入 Investment  
- [ ] Timeline `from_session_bars`（或等价）；slice 按交易日/时长切窗  
- [ ] 抽出 `FillMatcher`，默认 = 现日线成交；策略/MP 可覆写  
- [ ] K 线时间字段 + minute contract + AsOfSlice 对齐  
- [ ] 日线回归：`interval=1d` 行为与改前一致；再加分钟 smoke  

### 3.4 第三步明确不做（除非另开）

- Tick/L2 真实队列撮合、集合竞价精细模拟  
- 期权期货合约生命周期  
- Agent/UI timeframe 全量（可后置最小 timeframe 选择）

---

## 三步做完后还缺什么？

三步 = 引擎规则与时钟。UI / Agent / 衍生品 / 实盘等仍后置。

**数据本身不由框架提供**（A 一套、港一套、美一套，都在 userspace）。框架要做的是：让「数据 pack」能挂上来且引擎读得懂。

### 应用数据如何在框架内「够用」

已有分工（保持）：

```text
userspace  Provider/Handler/mapping  →  写入 sys_* / cust_*
core       tables + DataManager + data_contract loader  →  策略 issue(key)
market_profile  只管交易规则，不负责拉行情
```

每个市场 = 一个 **userspace data pack**（handlers + 填哪些表 + 可选 config），不是改 core 内置一套美股 SDK。

| Pack 至少要填满（日线权益最小集） | 对应契约 |
|----------------------------------|----------|
| 标的列表 | `stock.list`（或用户 key） |
| 日 K | `stock.kline.daily` |
| 交易日历行（带 `market=`） | `trade.calendar` |
| （可选）复权/停牌/行业… | 按市场需要，A 股才有 ST 等 |

**框架侧只需变「薄」的几件事（否则 pack 填了也跑歪）：**

1. **MP ↔ 数据声明**：profile 带 `calendar_market_id` + 最小 `required_contract_keys` / 可选 keys（A 才 auto-inject `stock.st_periods`）。  
2. **ID 约定**：同一库多市场 → 代码命名空间不撞（如 `xxx.SZ` / `xxxx.HK` / `AAPL.US`）；策略 universe 按 profile/list 过滤，勿默认全表当 A 股。  
3. **读路径跟 profile**：日历 `market=`、列表 filter、复权模式（美/港未必 `load_qfq_split`）不要写死 SSE/A 股。  
4. **Pack 注册留在 userspace**：`mapping.py` 增 handlers 即可；core 不内置 vendor。

**框架不要做的：** 内置港美数据、vendor token、每市场复制一套 SW/宏观表。

**一句话：** 三套数据 = 三套（或叠加）userspace pack；框架保证 **表形状 + contract + 按 profile 选日历/宇宙/可选依赖**，不保证行情内容。

## 参考路径


- `core/modules/market_profile/`
- `core/modules/market_profile/core/base/market_base_rules.py`
- `core/modules/market_profile/core/services/matching_service.py`（仅 ID matching，非撮合）
- `core/modules/strategy/.../investment/investment.py`（现成交逻辑）
- `core/modules/backtest_engine/core/timeline/timeline.py`
- `core/tables/stock/stock_klines/schema.py`
