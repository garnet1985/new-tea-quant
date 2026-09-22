# StrategyHooks / Context 重构（目标 0.6.0）

**状态：** 设计中，**不在当前版本实施**（破坏性改动）。  
**范围：** 用户可见钩子改名/删减/新增 + Context 分类（含 `state`）与钩子专用载荷分离。  
**相关讨论：** 2026-09 会话（随机策略简化 → 钩子表面 → ctx 与当次数据分离）。

---

## 1. 为什么等到 0.6.0

- 钩子方法改名 / 删除 / 改签名，所有 userspace `strategy.py` 与文档同步炸裂。
- 新增 `to_sample_list` 改变指纹前 `entity_ids` 解析路径（`execute_fp.scope`）。
- 需与 Context 分类 + 钩子载荷分离一并设计，避免 0.5.x 连改两次。

---

## 2. 定稿方向：用户可见钩子

```text
to_sample_list(ctx, stock_list) -> list[str]
on_calendar_slice(ctx, calendar_slice) -> list[str]
is_opportunity(ctx, records) -> bool
select_portfolio_entries(ctx, opportunities) -> Sequence[Opportunity|str]
is_stop_loss(ctx, records, *, custom, stage) -> bool    # custom/stage 仍建议保留，见 §4
is_take_profit(ctx, records, *, custom, stage) -> bool
```

| 新名 | 现状 | 时机 | 职责 |
|------|------|------|------|
| `to_sample_list` | **新增** | 整个回测 **一次**，**指纹生成之前** | 过滤全局宇宙 → ∩ DB 实可用 → 排序写入 `execute_fp.scope` 并钉进 `ctx.sample_list` |
| `on_calendar_slice` | `on_calendar_asof` | 仅 `slice_based` 每个日历日 | 入参带当日片；返回进入 `is_opportunity` 的 id 列表；日期藏在 slice 里 |
| `is_opportunity` | `has_opportunity` | 每实体每日 | `(ctx, records)`；bool；True 后框架建 `Opportunity` |
| `select_portfolio_entries` | `on_pick_portfolio_member` | 组合入场 | `(ctx, opportunities)` → 机会或 id 列表；未 override 走默认 |
| `is_stop_loss` / `is_take_profit` | 同名 | goal 段 `custom` 时 | 见 §4；需要当日 `records` + 明确在评哪一段 custom |

### 删除（不对用户暴露）

| 现状 | 处理 |
|------|------|
| `calendar_asof_needs_by_entity` | 删除；是否组全宇宙片留引擎内部 |
| `on_before_scan` / `on_after_scan` | 删除 |
| Hooks 上的糖（`signal_date` / `core_*` / `deterministic_roll`） | 删除 |

---

## 3. Context 结构 vs 钩子载荷（已澄清）

### 3.1 核心思想（已钉死）

**用户一眼看到两样东西：**

1. **当前我知道的** → 稳定的 `ctx`（所有钩子里长得一样）
2. **当前需要我操作的** → 显式入参（`records` / `calendar_slice` / `opportunities` / `stock_list`）

禁止再出现：`ctx.data` 里一会有 `opportunities`、一会有 records、一会又是 `by_entity`——字段「有时有有时没有」会大幅抬高学习成本。

`ctx` 全程同一套表面；当次操作对象只出现在参数列表里，不塞进 `ctx`。

### 3.2 Context 内部分类（用户可见）

`ctx` 仍是一个对象，内部按大类组织；其中一类是 **`state`**：

| 分类 | 路径示例 | 作用 |
|------|----------|------|
| 身份 / 配置 | `ctx.info`、`ctx.effective_settings`、`ctx.sample_list`、`ctx.mode` | 开跑后相对稳定；sample_list 由 `to_sample_list` 钉死并进指纹 |
| **运行时状态** | **`ctx.state.*`** | **跨回测日历**的数据存储（用户跨日变量等） |
| 归因 | `ctx.capture(...)` | 本笔信号快照 |

说明：

- `state` **是 Context 的一部分**（`ctx.state.xxx`），不是与 ctx 并列的顶层类型。
- `state` 会随日历推进而变；这不违背「载荷外置」——变的是跨日袋，不是「今日这只股票的 K 线」。
- 引擎 `assemble` / `fill` / `refill` **不对用户出现在 Context 表面**。
- 单股序列 / 横截面片 / 当日机会列表 **不进 ctx**，只作钩子入参。

### 3.3 钩子载荷（显式入参）

**`Records`（可叫 `data`）** — `is_opportunity` / stop-take  

- 单只股票、当前 as-of 下各 DataKey 序列  
- 快捷：`record_of_today`、`get_record(date)`、`get_records(start, end)`、`last(n)` 等  

**`CalendarSlice`** — `on_calendar_slice`  

- 当日横截面多股合集 + 日历旗标；日期对用户隐形  
- 薄快捷：`ids()`、按 id 取 records 等  

**`Opportunities`** — `select_portfolio_entries`  

- 当日机会集合；可 `to_ids` / 按 id 取等  

**`stock_list`** — `to_sample_list` 入参；结果进 `ctx.sample_list`  

学 `is_opportunity` 只需 `ctx` + `Records`；学横截面再加 `CalendarSlice`——不必先吞万能 ctx。

---

## 4. 钩子签名意见

| 草案 | 看法 |
|------|------|
| `to_sample_list(ctx, stock_list)` | 赞成；结果钉进 `ctx.sample_list` 并进指纹 |
| `on_calendar_slice(ctx, calendar_slice) -> list[str]` | 赞成；日期隐形 |
| `is_opportunity(ctx, records)` | 赞成 |
| `select_portfolio_entries(ctx, opportunities)` | 赞成 |
| `is_stop_loss(ctx, records)` 且 custom 只在 ctx | **部分赞成**：goal 配置可在 settings；但引擎问的是「**这一段** custom」。建议仍显式 `custom`（与可选 `stage`）或小的 `GoalCheck` |

`ctx.state`：跨日存储的正式位置（可替代或包装现有 remember/recall/forget）。

---

## 5. `to_sample_list` 与指纹（流水线定稿）

与现有 `settings.sampling`（`StockSampler`：uniform / pool / blacklist / …）的关系：

```text
1. DB / GlobalEntityCache 得到全市场 stock_list
2. settings.sampling 过滤（use_sampling=False 则跳过）
3. to_sample_list(ctx, stock_list)     # 回测只调一次；语义过滤
4. （可选）∩「DB 有数据」——默认不做，见下
5. sorted unique → 钉进 scope / ctx.sample_list → 算 execute_fp
```

**分工**

| 步 | 谁 | 干什么 |
|----|-----|--------|
| sampling | 配置声明 | 机械缩池：抽 N 只、白名单、黑名单、seed 随机 |
| `to_sample_list` | 策略代码 | 语义过滤：板块、规则、演示宇宙等（须确定性） |

**关于第 4 步「和 DB 有数据取交」：建议默认不做。**

- `GlobalEntityCache.get_stock_list()` 已是库侧可用宇宙；扫到无 K 线时引擎本就会跳过。
- 指纹前按区间查「是否有 bar」成本高，且数据补齐会让 **同 settings 换号**（像环境漂移），不宜塞进 `execute_fp.scope`。
- 若将来要「只跑有完整数据的票」，做成显式、可配置的预检，并想清楚是进 scope 还是仅运行时跳过。

**现状缺口（实施时要改）**

今天 `simulate` 用**全市场** list 算指纹，`sampling` 在 enumerator pipeline 里才缩池——scope 与真实扫描池不一致。0.6.0 应把「sampling + `to_sample_list`」挪到**指纹之前**，使 `execute_fp.scope.entity_ids` = 实入池。

约束：钩子确定性；指纹只放实入池；钩子源码→`env_fp`，`sampling`/`core`→`execute_fp`。

---

## 6. 实施改动面（备忘，不实施）

- hooks base、enumerator/scanner/portfolio/investment、simulate 指纹前路径
- 新建：`Records` / `CalendarSlice` / `Opportunities`；Context 内建 `state`；钩子专用数据不进 ctx
- userspace demos + 文档；CHANGELOG Breaking + 迁移说明
- Tag 平行钩子是否跟名：另开

---

## 7. 开放问题

- [x] ~~核心 UX~~ → **「我知道的」= 稳定 ctx；「要我操作的」= 显式入参**；禁止 ctx 里按钩子时有时无的 data 口袋
- [x] ~~State 是否独立于 Context~~ → **否**；`ctx.state` 是 Context 的一类
- [x] ~~`watch_list` / sampling ↔ `to_sample_list` 顺序~~ → **DB → settings.sampling → 钩子 →（默认不做有数据交）→ 指纹**
- [ ] `scanner.watch_list` 是否并入 sampling 之前的配置过滤（与 pool 策略如何并存）
- [ ] `ctx.state` 与现有 `remember` / `capture` 的边界（state 存跨日；capture 仍归因？）
- [ ] `on_calendar_slice` 是否完全放弃 `session_state`（现 `CalendarAsOfResult`）？
- [ ] `is_stop_loss`：保留 `custom`/`stage` 还是引入 `GoalCheck`？
- [ ] 类型命名：`Records` vs `data`；`sample_list` vs `stock_list`
