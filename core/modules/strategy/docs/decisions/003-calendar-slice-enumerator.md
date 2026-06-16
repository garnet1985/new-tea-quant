# Decision 003: Calendar Slice Enumerator（分片枚举器）

## Status

**Accepted**（架构方向已定；实现待落地）

## Context

Strategy 枚举在「全窗 × 全 universe」下 bulk 加载 K 线（及关联 contract）时，**IO 与内存**是主要成本。现有 **`entity_timeline`**（每股独立时间线、逐 bar 扫描）在多数策略上仍是最自然、**长期保留**的默认模式；部分策略需要 **同步交易日历 + 滚动时间窗控内存**，故 **新增** **`calendar_slice`** 与之并列，而非替换或淘汰前者。

团队在 `experiments/` 下完成了一组探针（MySQL 只读为主，DuckDB isolated snapshot 对照），覆盖：

| 实验 | 目录 | 结论摘要 |
| --- | --- | --- |
| K 线 bulk / 切片 IO | [`experiments/kline_slice_io_profile/`](../../../../../experiments/kline_slice_io_profile/) | 瓶颈在 **bulk DB read + RSS**；单片 ~500 股 × 1 年 daily+weekly qfq ≈ **200MB** 量级 |
| 3 段 warm-up / prefetch | 同上 `profile_three_year_slice.py` | prefetch 仅当 **compute ≥ 下一片 load** 且有 **长驻 Reader** 时划算；每片 spawn 冷启动常亏 |
| 横截面 loop vs df | [`experiments/cross_section_select/`](../../../../../experiments/cross_section_select/) | 简单 filter+sort **毫秒级**；**loop + dict** 快于 DataFrame；双表 join 在 select 阶段做 dict 对齐即可 |
| 双表（kline + indicators） | 同上 `benchmark_low_price_cap_monthly.py` | IO **~16s**（两表串行 batch）；select **~0.02s** |
| 窗长缩放 / 冷 vs 热 | 同上 `profile_load_window_scaling.py` | 连接 pre-warm 后 **cold ≈ warm (~1.0×)**；慢在行数+双表，非首连；短窗有 **~0.3s fixed cost** |

用户策略逻辑（`scan_opportunity`）**不可控**；枚举器只能优化 **可见区：读什么、何时读、读多少、怎么喂数据**。

## Decision

### 1. 双模式并列（非淘汰旧模式）

**两种 `simulation.execution_mode` 长期并存：**

| 模式 | 说明 | 默认 |
| --- | --- | --- |
| **`entity_timeline`** | 现有行为：每股 job、实体时间线、仅 `scan_opportunity` | **是** |
| **`calendar_slice`** | 新增：同步日历、分片 IO、`on_calendar_asof` + `scan_opportunity` | opt-in |

- 未配置或 `entity_timeline` 时走现有 **`OpportunityEnumeratorFlow`**，行为与今日一致。
- 显式 **`calendar_slice`** 时走 **`CalendarSliceEnumeratorFlow`**；**不在** `OpportunityEnumeratorWorker` 主路径堆 `if slice`。
- **`simulation.slice_open_days`** 仅 `calendar_slice` 生效；须经 **系统 clamp**（Appendix A.1）。
- 两种模式 **共享**：`BacktestCalendarContext`、`StrategyJobContractBatch`、`load_batch` / contract issue；**`scan_opportunity(dict, settings)` 签名不变**。
- **`calendar_slice` 新增**：**`on_calendar_asof(ctx, settings)`** → 对选中股 **`scan_opportunity`**。
- 枚举产出 **同一份 CSV contract**；**Price / Capital 回放路径不改**。
- 用户面向模型保持 **loop + dict per stock**；**不以 DataFrame / 矩阵为双模式主引擎**。
- **Portfolio** `on_portfolio_select`（Top-K 等）与 enum 正交，推迟至 **0.5.x**。

### 2. 切片模型（SlicePlanner）

- 二维分片：**`(calendar_window × universe_chunk)`**。
- 切分顺序：**先时间窗，再 universe chunk**（与 `(stock_ids, date_range)` batch IO 自然对齐）。
- 复用 [`dispatch_planner`](../../../../infra/worker/dispatch_planner.py) 的 memory / entities 规划思路，按探针反推 chunk 大小。
- 时间边界对齐 **开市日历**（`sys_trade_calendar`）；有完整日历时按 **calendar year / 配置窗**，无数据时再 fallback（实验：`auto_thirds`）。

### 3. Reader Lane ∥ Compute Lane（双进程 + 队列）

```
┌─────────────────┐     Q (depth 1~2)     ┌─────────────────┐
│  Reader 进程池   │ ────────────────────▶ │  Compute 进程池  │
│  bulk load_batch │                       │  scan_opportunity│
│  只读 DB         │                       │  不连 DB *       │
└─────────────────┘                       └─────────────────┘
        │ prefetch 下一片 / warm-up                │ carry state
        ▼                                          ▼
   SlicePayload                              合并 → 同 CSV contract
```

- **Reader**：长驻进程/线程，按 slice plan 执行 bulk load（各 contract **batch 一次**），将 **`SlicePayload`** 放入队列。
- **Compute**：从 Q 取片，对 `Dict[stock_id → rows]`（或 date 索引）跑 `scan_opportunity`；片间 **carry** 指标/lookback 状态。
- **Warm-up**：下一片可在 compute 当前片时 **preload 进 Q**；warm-up 片 **不写 CSV**，仅喂状态/指标窗口。
- **Q 深度**：默认 **1**（必要时 2）；与内存峰值模型联动（见 §5）。
- **Prefetch 开关**：可关闭；关闭则牺牲 overlap 换更低峰值内存。
- \* **DuckDB**：Compute **不得**持有 live 库连接；Reader 释放/独占策略见 §4。

**禁止**：每片 `Process(spawn)` 临时读库（实验证冷启动 > 短 compute 的 overlap 收益）。

### 4. 存储形态与 Join

- IO 结果保持 **`load_batch` 返回形态**：`Dict[stock_id → List[dict]]`，或 prep 为 `Dict[stock_id → Dict[date → field]]`。
- **多 contract**（如 kline + indicators）：各表 **各一次 batch**，**不在 SQL 层 heavy join**；在 compute/select 时按 **`(stock_id, date)`** 内存对齐（实验：join 成本 ≪ IO）。
- DataFrame 仅允许 **策略内部可选 helper**；枚举器主路径 **不强制** pandas。

### 5. 内存峰值模型（2～3 片）与探针

运行期可能同时存在：

| 片 | 角色 |
| --- | --- |
| `slice[i-1]` | 交界 lookback，compute 仍需要回溯 |
| `slice[i]` | 当前 compute |
| `slice[i+1]` | preload 已完成，在 Q 中等待 |

Planner 与运行时须按 **peak_slices ∈ {2, 3}** 预算，而非单片 ×1。

**静态探针（规划期）**

- 运行 [`profile_kline_load`](../../../../../experiments/kline_slice_io_profile/profile_kline_load.py) 等脚本，记录 `rss_delta_mb`、`rows/stock` per `(chunk, window, terms, adjust)`。
- 写入 settings / fingerprint 字段，例如 `slice.memory_probe_mb_per_slice`。
- `memory_budget_mb ≈ probe × peak_slices × safety_factor`（建议 safety **1.2～1.5**）。

**动态监控（运行期）**

- 每片 load 后记录：`rss_mb`、行数、Q 中 pending 片数、contract 列表。
- 超 `memory_budget_mb` 时按序降级：
  1. 停止 prefetch（峰值 3→2）
  2. 缩小 `universe_chunk` 或 `calendar_window`
  3. 显式 `release_slice` + `gc`
  4. 失败则 abort，并输出诊断（哪片、多少 MB、哪张表）

**Settings 语义开关**

| 开关 | 作用 |
| --- | --- |
| `prefetch_enabled` | 控制是否 preload 进 Q |
| `retain_previous_slice` | 交界 lookback 需要时保留老片 |
| `peak_slice_budget` | 显式 2 或 3，供 Planner 使用 |

### 6. DuckDB 与 MySQL 的差异

| 后端 | 多进程并行 load 同一库 | Reader 建议 |
| --- | --- | --- |
| **MySQL** | 多连接 **只读** 可并发；多 contract **可分 Reader 并行**（Phase 2 可选，理论 IO ≈ max(各表)） | 长驻 Reader；compute 不连库 |
| **DuckDB** | **同一 `.duckdb` 文件** 多进程同时 bulk read **高阻力/易失败**（文件锁、WAL）；勿等同于 MySQL | **单 Reader 进程、contract 串行 load**；或 **snapshot 副本** 只读（空间换时间）。Compute 不连 live 库。主进程在 worker 池前须 **`release_all_main_db_handles`**（见 [`process_pool_scope`](../../../../infra/db/engines/duckdb/process_pool_scope.py)） |

**推论（可选 Phase 2）**：「不同 contract 不同进程读再 merge」—— **MySQL 可试**；**DuckDB 默认不做**，除非只读 snapshot 且仍接受单文件串行。

### 7. 实验数据锚点（MySQL，500 股，qfq，2023—2025）

供 Planner 量级参考（非 SLA）：

| 场景 | 量级 |
| --- | --- |
| 3 年 daily+weekly bulk | ~11s，~398k rows，RSS Δ ~530MB |
| daily 单表 bulk | ~9.7s，~328k rows |
| kline + indicators 双表 IO | ~16.4s（~9.5s + ~6.9s 串行） |
| 36 次月度横截面 select（单表 / 双表） | **~0.01～0.03s** total |
| loop vs df select（单表，groupby 后） | loop **~2×** 快于 df；naive df 全表扫 **~35×** 慢 |

**结论**：优化火力集中在 **Reader / SlicePlanner / Q**；不要为 enum 主路径引入 df 引擎。

### 8. 窗长缩放与 IO 模型（`profile_load_window_scaling`）

固定 500 股、起点 `20230101`、daily + indicators、qfq（MySQL 只读）：

| 窗长 | kline | indicators | **IO 合计** | rows |
| --- | ---: | ---: | ---: | ---: |
| 3mo | 0.65s | 0.58s | **1.23s** | 25k |
| 6mo | 1.37s | 1.10s | **2.47s** | 51k |
| 12mo | 2.38s | 2.23s | **4.61s** | 106k |
| 36mo | 10.35s | 6.84s | **17.18s** | 328k |

- 连接池 **pre-warm 后** 同窗重跑 cold ≈ warm（~**1.0×**）→ 瓶颈不是「冷启动」，是 **行数 + 双表串行 IO**。
- kline 拟合（12mo 以上较准）：`T_load ≈ T_fixed + k × rows`，短窗有 **~+0.3s 底数**，**k ≈ 33µs/row**。
- 双表合计约 **`k ≈ 27µs/row`**；MySQL 上 **分 contract 并行 Reader** 可将总 IO 从「相加」压向 **`max(各表)`**。

### 9. 内存预算兑换率（小 slice ↔ Q 深度 ↔ 并行 warm-up）

**Accepted 推论**（Planner 设计约束）：

在 **固定 `memory_budget_mb`** 下，三者可交换：

```text
calendar_window 粒度  ↔  Q 中 warm-up 片数  ↔  Reader 并行度（MySQL）
```

| 机制 | 作用 |
| --- | --- |
| **更小 calendar slice** | 单片 RSS ∝ 行数 ↓；同样 peak 片数下 **内存压力 ↓** |
| **同等 MB 预算** | 单片变小 → 可 **加深 Q**（多片 preload）或 **多 Reader 并行 warm-up**（MySQL） |
| **并行 warm-up** | 当 `T_compute ≪ T_load` 时减少 **等 Q** 空档；不减少总行数，只改善 **wall overlap** |
| **代价** | 片数 ↑ → **fixed cost × N** 与 carry/merge handoff ↑；Planner 须对冲 |

**DuckDB**：并行 warm-up **不增加** 同一 live 文件读吞吐；兑换仅体现在 **更小片 / Q 深度**。

**Planner 目标（概念）**：在 `memory_budget_mb` 约束下最小化  
`Σ max(0, T_load(next) − T_compute(current))`；降级顺序：停 prefetch → 缩 chunk/窗 → release_slice → abort。

## Consequences

- 新增 **`calendar_slice`** 编排与 Reader/Compute 队列协议；**`entity_timeline` 仍为默认且完整维护**。
- 需实现 **内存探针 + 运行时 RSS 护栏**，否则 prefetch 在三片峰值下 OOM 风险高。
- DuckDB 部署下 **Reader 并行度受限**；多 contract 并行读属 MySQL 优化项，非通用假设。
- `scan_opportunity` 与 CSV contract **保持稳定**，Price/Capital/指纹复用逻辑可渐进迁移。
- Portfolio 选股层仍后置于 0.5.x，enum 只负责 universe 机会列（含 `extra_fields` 预留）。

## References

- [ADR-004 Runtime Planner](./004-calendar-slice-runtime-planner.md)
- 实验索引：[`experiments/README.md`](../../../../../experiments/README.md)
- K 线切片 IO：[`experiments/kline_slice_io_profile/README.md`](../../../../../experiments/kline_slice_io_profile/README.md)
- 横截面选股：[`experiments/cross_section_select/README.md`](../../../../../experiments/cross_section_select/README.md)
- DuckDB 多进程锁：[`core/infra/db/docs/storage-domains.md`](../../../../infra/db/docs/storage-domains.md)
- 枚举复用（正交）：[`001-enumerator-reuse-by-containment.md`](./001-enumerator-reuse-by-containment.md)

## Open Items（实现阶段再定）

- ~~`SlicePayload` / Q 消息 schema~~ → v2 已落地；`SliceDone` 含 load/compute timing。
- **Runtime Planner 动态细节**：v1 已落地 auto + 每片 preload 调节；见 [ADR-004](./004-calendar-slice-runtime-planner.md)。
- warm-up 片释放老片的精确条件（交界 bar 索引与指标 window 长度）。

---

## Appendix A: Settings 与用户 API（部分 Accepted）

**已拍板（2026-03）：**

1. **`simulation.execution_mode`**：`entity_timeline` | `calendar_slice`
2. **`simulation.slice_open_days`**：每片开市日数，**系统 clamp**
3. **用户 API**：`entity_timeline` 仅 `scan_opportunity`；`calendar_slice` 为 `on_calendar_asof` + `scan_opportunity`
4. **`on_calendar_asof` 调用频率**：本片内 **每个开市日** 各调用一次（与 `entity_timeline` 每股逐 bar 同频，但改为 **全 universe 同步 as_of**）

---

### A.1 Settings（`simulation` 块，非 `enumerator`）

```python
"simulation": {
  "template": "standard",                    # 现有字段不变
  "execution_mode": "entity_timeline",       # default | "calendar_slice"
  "slice_open_days": 63,                     # 仅 calendar_slice；每片开市日数（非自然日）
  # ... monitor_price_model / buy / sell 等现有字段
}
```

**`slice_open_days` 系统管控（validate + Planner clamp）**

| 规则 | 说明 |
| --- | --- |
| **下限** | `≥ data.min_required_records` 与指标 lookback 所需开市日（取 max） |
| **上限** | 由 **`memory_budget_mb` ÷ (probe_mb_per_open_day × peak_slice_budget)`** 反推；超出则 **validate 拒绝** 或 run 前 **clamp 到 max** 并 warn |
| **探针** | `profile_load_window_scaling` / `probe_slice_io` 给出 `mb_per_row`、`peak_slices`；与 [`dispatch_planner`](../../../../infra/worker/dispatch_planner.py) 的 `memory_floor_mb` 同源 |
| **UI** | 工作台 simulation 面板：slider 或枚举档（如 21 / 42 / 63 / 126），**不可自由填任意整数**（或填了也被 clamp） |

**仍放 `enumerator` 的运行参数**（非用户策略语义）：`max_workers`、`is_verbose`、prefetch / Reader 并行等（实现期 `enumerator.calendar_slice_runtime` 或系统默认）。

**指纹**：`simulation.execution_mode`、`simulation.slice_open_days` 参与 `StrategyRunFingerprint`。

### A.2 用户 Strategy Worker API

**`entity_timeline`（默认）— 不变**

```python
def scan_opportunity(self, data: dict, settings: dict) -> Optional[Opportunity]:
    ...
```

**`calendar_slice` — 在上一模式基础上多一层**

```python
def on_calendar_asof(
    self,
    ctx: CalendarAsOfContext,
    settings: dict,
) -> CalendarAsOfResult:
    """
    同步日历：本片内每个开市日各调用一次（as_of = 当日 cal_date）。
    ctx.stocks：本片 universe 在 as_of 及 lookback 窗内的 per-stock 数据。
    返回本日要进入 scan_opportunity 的 stock_ids（可为空）；可写 carry。
    若策略仅在某些日换仓（如月初），在 on 内自行判断 as_of 即可。
    """

def scan_opportunity(self, data: dict, settings: dict) -> Optional[Opportunity]:
    """仅对 on_calendar_asof 选中的股调用；data = ctx.stocks[sid] merged overrides。"""
```

```python
@dataclass
class CalendarAsOfContext:
    as_of_date: str
    slice_id: str
    slice_open_days: int
    window_start: str
    window_end: str
    stocks: dict[str, dict]
    carry: dict[str, Any]
    open_date_index: int                 # 本片内第几个开市日（0-based）
    is_first_open_of_month: bool        # 信息字段；框架填，供策略判断是否 rebalance

@dataclass
class CalendarAsOfResult:
    selected_stock_ids: list[str]
    stock_overrides: dict[str, dict] = field(default_factory=dict)
    carry: dict[str, dict] = field(default_factory=dict)
```

**Advanced（可选，v1 可不实现）**：若实现 `scan_opportunities_at_asof(ctx, settings) -> list[Opportunity]`，框架跳过 on+scan 两阶段。

**命名说明**：用户层用 **calendar / as_of**；IO 层 **SlicePayload** 不叫 `on_slice`，避免与 Reader 内存片混淆。

### A.3 框架对接

```python
# SimulationSettings / validate
execution_mode = simulation.get("execution_mode", "entity_timeline")
slice_open_days = clamp_slice_open_days(
    simulation.get("slice_open_days"),
    settings_view=...,
    probe=...,
)

# EnumeratorRuntimeService.build_context
if execution_mode == "calendar_slice":
    flow = CalendarSliceEnumeratorFlow(...)
else:
    flow = OpportunityEnumeratorFlow(...)
```

**CalendarSliceEnumeratorWorker**（概念循环）：

```text
foreach SlicePayload:
  carry = payload.carry_in
  foreach as_of in open_dates(window_start, window_end):   # 每个开市日
    ctx = build_context(as_of, stocks=..., carry=carry)
    result = worker.on_calendar_asof(ctx, settings)
    carry = result.carry
    foreach sid in result.selected_stock_ids:
      opp = worker.scan_opportunity(merged_data(sid), settings)
      framework.stamp_and_track(opp)            # 与 entity_timeline enum 相同后续
```

### A.4 运行时类型（Planner / Reader，略）

（见原 A.2 模块路径：`SliceDescriptor`、`SlicePayload`、`SlicePlanner`；`slice_open_days` 驱动 Planner 切 calendar 窗。）

### A.5 不变契约

| 面 | `entity_timeline` | `calendar_slice` |
| --- | --- | --- |
| 用户钩子 | `scan_opportunity` | `on_calendar_asof` + `scan_opportunity` |
| CSV / Price / Capital | **同 schema** | **同 schema** |

### A.6 仍待实现期敲定

1. **Compute job 粒度**：slice job（推荐）vs stock job  
2. **`SliceCarryState` vs `CalendarAsOfResult.carry`** 合并规则  
3. **Reader**：DataContractManager.issue vs 直连 DataManager
