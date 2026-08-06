# 性能测试用例 — 回测引擎

**位置：** `__performance__/`

---

## 测什么

用两套**固定空策略**（不选股、不产生交易机会）测引擎跑得有多快。  
**按股票分包（entity）** 和 **按时间切片（slice）** 用不同命令分开跑；算法不同，**不要直接比谁更快**。

测试数据直接写入临时库（默认 DuckDB，目录 `.db/`），不经过 CSV。规模见 `scripts/cmd/config.py`（当前约 1000 股 × 3 年）。前提全文：[`reports/test_preconditions.md`](./reports/test_preconditions.md)。

## 做什么 / 不做什么

**做**

- `bpe`：按股票分包模式
- `bps`：按时间切片模式

**不做**

- 不评价选股好不好（机会数恒为 0）
- 不做功能对错回归（那是 `__test__/`）
- 不追求还原真实行情

---

## 基准策略（请勿改运行模式和空策略逻辑）

| 目录 | 模式 | 命令 |
|------|------|------|
| `scripts/test_strategies/entity_based/` | 按股票分包 | `bpe` |
| `scripts/test_strategies/slice_based/` | 按时间切片 | `bps` |

时间窗口和股票池由 `cmd/run.py` 按临时库里的数据集信息注入；策略文件本身保持稳定。

空策略：每天不选任何股票，只测引擎「装数据 → 按日历往前走」的速度。

---

## 场景：按股票分包

| 项 | 内容 |
|----|------|
| **目的** | 全段时间一次装载时的总执行时间 |
| **命令** | `python devcli.py bpe` |
| **结果** | `reports/{BE版本}/entity_based/{duckdb\|mysql\|pgsql}/` |

---

## 场景：按时间切片

| 项 | 内容 |
|----|------|
| **目的** | 按时间片读数据、推进日历时的总执行时间 |
| **命令** | `python devcli.py bps` |
| **结果** | `reports/{BE版本}/slice_based/{duckdb\|mysql\|pgsql}/` |
| **关注** | 总执行时间、每只股票装载几次、一共切了几片、读数据进程数、预读排队深度 |
