# 性能测试用例 — Backtest Engine

**模块：** `modules.backtest_engine`  
**位置：** `__performance__/`

---

## Scope

验证合成数据上的 BE 墙钟。  
**默认**经 Strategy 枚举栈（`scripts/strategies/perf_null` → `EnumeratorPipeline` → BE entity / slice）。  
idle 测调度空转下限。不测完整 price_factor / portfolio。

## 边界

**负责**

- 默认：`EnumeratorPipeline.run`（entity_based + slice_based）
- 可选：BE 公开 API 的 idle / 手搓 io

**不负责**

- 完整策略业务（机会产出恒为 null）
- 功能正确性（→ `__test__/`）

---

## 输入

| 名称 | 生成 | 说明 |
|------|------|------|
| `fake_data/` | `scripts/data_gen.py` | 10 股 × 2024；仅 daily |
| `scripts/strategies/perf_null/` | 手写 | null hooks；mode 由 `test_script` 注入 |

---

## Scenario：`strategy_enum_entity` / `strategy_enum_slice`（默认）

| 项 | 内容 |
|----|------|
| **目的** | 实战枚举路径墙钟（读 K + 切片；无机会产出） |
| **脚本** | `test_script.py`（`--case all` 或 `--case strategy_enumerate` = 两者） |
| **结果** | `results/_local/strategy_enum_entity/`、`…/strategy_enum_slice/` |
| **关注指标** | wall_time、elapsed_seconds、success、opportunities_count（期望 0） |

```bash
python core/modules/backtest_engine/__performance__/scripts/test_script.py --case strategy_enum_entity
python core/modules/backtest_engine/__performance__/scripts/test_script.py --case strategy_enum_slice
```

---

## Scenario：`idle_*`

调度空转下限。`--idle` 或 `--case idle_*`。  
**勿**与真实回测墙钟对比；对比请用 `strategy_enum_*`。

---

## Scenario：`io_*`（非默认）

手搓 `load_batch` + as-of；仅遗留对比。
