# 性能测试用例 — Backtest Engine

**模块：** `modules.backtest_engine`  
**位置：** `__performance__/`

---

## Scope

用固定 null 基准策略测 BE 墙钟。**entity / slice 分开命令**，算法不同，结果不可混比。

数据由 `cmd/db_creation.py` **直接注入**临时 DuckDB（连续假 ID + 固定规律 K 线），无 CSV 中间层。

## 边界

**负责**

- `be_perf_entity` → `EnumeratorPipeline` → BE `entity_based`
- `be_perf_slice` → `EnumeratorPipeline` → BE `slice_based`（`SliceOrchestrator`）

**不负责**

- 策略业务正确性（机会恒为 0）
- 功能回归（→ `__test__/`）
- 真实行情还原

---

## 基准策略（勿改 mode / hooks）

| 目录 | mode | 命令 |
|------|------|------|
| `scripts/test_strategies/be_perf_entity/` | `entity_based` | `bpe` |
| `scripts/test_strategies/be_perf_slice/` | `slice_based` | `bps` |

窗口与股票池由 `cmd/run.py` 按 registry 中的 dataset meta 注入；策略文件本身保持稳定。

基准 hooks：`on_calendar_asof` 返回空 `stocks`（测 BE 装载/切窗/tick，**不**每天全宇宙 scan）。

---

## Scenario：`be_perf_entity`

| 项 | 内容 |
|----|------|
| **目的** | entity_based 全窗装载墙钟 |
| **命令** | `python devcli.py bpe` |
| **结果** | `results/_local/be_perf_entity/` |

---

## Scenario：`be_perf_slice`

| 项 | 内容 |
|----|------|
| **目的** | slice_based 按正式片 IO 墙钟 |
| **命令** | `python devcli.py bps` |
| **结果** | `results/_local/be_perf_slice/` |
| **关注** | wall_time、`per_entity_load_count`、`formal_slices_completed`、reader/queue |
