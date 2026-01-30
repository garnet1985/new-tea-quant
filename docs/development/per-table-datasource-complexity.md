# Per-Table Data Source 分表后的复杂度变化

在采用「data source ↔ table 一一对应、schema 共用」的前提下，对 **kline + daily_basic** 和 **price_indexes** 做分表后，复杂度的变化分析。

---

## 1. 当前架构简要

| 模块 | 现状 | 主要复杂度来源 |
|------|------|----------------|
| **Kline** | 1 个 Handler：4 个 API/股（daily_kline, weekly_kline, monthly_kline, daily_basic）→ **合并后写入同一张 kline 表** | 多 API 协同、按股分组、kline 与 basic 的 merge（JOIN + ffill）、两套 schema 合成一张表 |
| **price_indexes** | 1 个 Handler：4 个 API（cpi, ppi, pmi, money_supply）→ **按 date 合并后写入一张宽表** | 多 API 按 key 合并、宽 schema（20+ 字段）、消费端按字段子集读取 |

---

## 2. K线 + daily_basic 分表

### 2.1 当前复杂度（合并在一张表）

- **Job 编排**：每只股票 4 个 Job（3 个 kline + 1 个 daily_basic），且 daily_basic 的日期范围要跟 kline 对齐（取 min start、max end 等）。
- **执行后处理**：
  - 按 `stock_id` 分组；先收集所有 `daily_basic`，再按 term（daily/weekly/monthly）取 kline 与 basic **做 LEFT JOIN + ffill**。
  - `_merge_kline_and_basic`：字段映射（kline / basic 各一套）、合并键 `(id, date)`、basic 列 ffill、缺数填 0、去 `_basic` 后缀等。
- **Schema**：kline 表 = kline 字段 + daily_basic 字段，两套语义在一张表里。
- **代码量**：KlineHandler 中与「合并、basic 映射、按股分组写」相关的逻辑约 **250+ 行**（含 `_process_fetched_data_by_stock`、`_merge_kline_and_basic`、`_map_kline_fields`、`_map_basic_fields` 等）。

### 2.2 分表后（kline 表 / daily_basic 表 各一 data source）

- **kline 表**：data source 只负责 3 个 API（daily / weekly / monthly kline）→ 一种 schema（仅 kline 字段）→ **一张表**。  
  - 若进一步「per 周期 per 表」：可拆成 kline_daily / kline_weekly / kline_monthly，每个 data source 对应一张表，schema 与表一致。
- **daily_basic 表**：data source 只负责 1 个 API（daily_basic）→ 一种 schema（仅 basic 字段）→ **一张表**。

**复杂度下降：**

- **删除**：整块「按股合并 kline + basic」的逻辑（`_process_fetched_data_by_stock` 里对 basic 的收集、按 term 的 merge、`_merge_kline_and_basic`、`_map_basic_fields`、ffill/缺数处理等）。
- **简化**：Kline 侧不再需要「为 daily_basic 单独算日期范围、只调一次」的编排，改为标准 per-entity + 日期范围；daily_basic 侧变为标准单 API、单表写入。
- **Handler 形态**：Kline 可收敛为「仅 kline 3 个 API → 1 表或 3 表」的通用 pipeline；daily_basic 为「1 API → 1 表」的通用 pipeline，无需自定义 merge 钩子。
- **下游**：若策略/回测需要「K线 + 基本面」宽表，在**读时**做 JOIN（策略层或一个小型 service），而不是在 data source 层写表时合并。

**粗略量级**：KlineHandler 中与合并/分组合计约 **250+ 行** 可删除或大幅收缩，整体复杂度约降 **60%+**（以该 Handler 为基准）。

---

## 3. price_indexes 分表

### 3.1 当前复杂度（一张宽表）

- **合并**：4 个 API（cpi / ppi / pmi / money_supply）在框架层按 `merge_by_key: "date"` 合并成一条条「月度记录」，再写入一张表。
- **Schema**：单表 20+ 字段（cpi*, ppi*, pmi*, m0/m1/m2*），所有指标共用一个 `date`。
- **Handler**：`on_after_mapping` 里对**所有**指标统一做月份标准化、并为**全部**字段 setdefault（cpi/ppi/pmi/m0/m1/m2 等），逻辑与「多指标混在一张表」强绑定。
- **消费端**：MacroService 的 `load_cpi` / `load_ppi` / `load_pmi` / `load_money_supply` 实为「同一张表 + 按字段子集过滤」（`_load_price_indexes(..., fields=...)`）。

### 3.2 分表后（cpi / ppi / pmi / money_supply 各一表）

- **4 个 data source**：cpi → `cpi` 表，ppi → `ppi` 表，pmi → `pmi` 表，money_supply → `money_supply` 表。
- **Schema**：每个 data source 的 schema 与对应表一致（小 schema，约 4–10 个字段）。
- **无合并**：不再需要 `merge_by_key`，每个 Handler 单 API → 单表，无 `on_after_mapping` 里对其它指标字段的默认值处理。
- **消费端**：`load_cpi()` → `cpi_table.load()`，`load_ppi()` → `ppi_table.load()` 等，不再需要「从宽表里按 fields 过滤」。

**复杂度下降：**

- **删除**：PriceIndexesHandler 中「多 API 合并、宽表默认值、月份标准化里对 4 类指标混在一起」的逻辑；可改为 4 个轻量 Handler（或 1 个通用 Handler + 4 份 config）。
- **Schema**：从 1 个 20+ 字段的 schema 变为 4 个小 schema，每个与表一一对应。
- **框架**：不再依赖「多 API → merge_by_key → 单表」这条路径；全部走「单 API → 单表」标准路径。
- **MacroService**：从「一表 + 多字段子集」变为「四表、各读各的」，代码更直观，无字段过滤层。

**粗略量级**：PriceIndexesHandler 当前约 **130 行**，分表后每个小 Handler 可收敛到 **约 0~20 行**（仅保留月份标准化等可复用或放到基类），整体复杂度约降 **70%+**（以 price_index 相关 Handler + 消费端为基准）。

---

## 4. 汇总对比

| 项目 | 当前 | 分表后 | 复杂度变化 |
|------|------|--------|------------|
| **Kline + daily_basic** | 1 Handler，4 API/股，合并写入 1 表，大量 merge/ffill/映射 | 2（或 4）个 data source ↔ 2（或 4）张表，无 merge | **约降 60%+**（以 KlineHandler 为基准） |
| **price_indexes** | 1 Handler，4 API 合并为 1 宽表，消费端按字段子集读 | 4 个 data source ↔ 4 张表，消费端按表读 | **约降 70%+**（以 price_index 相关代码为基准） |
| **通用收益** | 多 API 协同、合并逻辑、宽表、字段子集读取 | 单 API → 单 schema → 单表，无合并、无字段过滤 | 代码路径统一、易测试、易扩展 |

---

## 5. 结论与建议

- **K线与 daily_basic 分表**：能去掉 KlineHandler 中绝大部分「按股、按周期合并 kline+basic」的定制逻辑，复杂度约降 **60%+**，且 schema 与表一致，后续做列存/回测也更清晰。
- **price_index 分表**：能去掉「多 API 按 date 合并 + 宽表 + 按字段子集读」的整条链路，改为 4 个「单 API → 单表」标准 data source，复杂度约降 **70%+**。
- 整体上，采用 **per-table data source（schema 共用、data source 与 table 一一对应）** 并做上述分表，能显著降低「合并、宽表、字段子集」带来的心智与实现负担，复杂度下降在 **约 60%~70%** 量级（按涉及 Handler + 消费端估算）。

若你希望，我可以再按「先 kline/daily_basic 分表」或「先 price_indexes 分表」给出一个具体改造步骤清单（含表名、Handler 拆分、MacroService 改动点）。
