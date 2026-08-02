# 性能测试用例 — Backtest Engine

**模块：** `modules.backtest_engine`  
**位置：** `__performance__/`

---

## Scope

验证 BE `entity_based` / `slice_based` 调度空转（合成数据）。不测 strategy/tag 业务钩子。

## 边界

**负责**

- BE 公开 `BacktestEngine.entity_based.run` / `slice_based.run` 的墙钟与调度行为
- 可选：execute_fn 内经 DataManager 读日 K（`--with-io`）

**不负责**

- strategy enumerate / tag execute 端到端
- 功能正确性（→ `__test__/`）

---

## 输入（fake_data/）

| 名称 | 生成 | 说明 |
|------|------|------|
| `fake_v1_experiment` | `scripts/data_gen.py` | 默认 10 stocks × 20230101–20251231，仅 `term=daily`；seed 固定 |

---

## Scenario：`idle_entity_based`

| 项 | 内容 |
|----|------|
| **目的** | entity 轴调度空转 |
| **脚本** | `scripts/test_script.py --case idle_entity_based` |
| **输入** | `fake_data/`（+ 可选 `.workdir` DuckDB） |
| **结果** | `results/_local/idle_entity_based/` |
| **关注指标** | wall_time、jobs、success |

```bash
python core/modules/backtest_engine/__performance__/scripts/test_script.py --case idle_entity_based
```

---

## Scenario：`idle_slice_based`

| 项 | 内容 |
|----|------|
| **目的** | slice 轴调度空转 |
| **脚本** | `scripts/test_script.py --case idle_slice_based` |
| **输入** | 同上 |
| **结果** | `results/_local/idle_slice_based/` |
| **关注指标** | wall_time、timeline_points、success |

```bash
python core/modules/backtest_engine/__performance__/scripts/test_script.py --case idle_slice_based
```

---

## 结果与版本对比

- 本地试跑：`results/_local/`（gitignore）
- 正式基线是否提交：样本规模定稿后再定
