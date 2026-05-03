# 策略 Settings 指纹策略

## 目标

建立稳定、可执行的规则，用于：

- **API settings** 形态规范化（避免同义不同形的 payload）
- **工作台 `settings_core`**：构建 **`settings_snapshot` 指纹** 时 **哪些字段参与、哪些剔除**（与 [`workbench-version-fingerprint.md`](./workbench-version-fingerprint.md) 一致）
- （历史）枚举器按磁盘结果做缓存命中时，字段策略与下文 **「剔除」** 一致；实现上为 **`StrategySettings.build_settings_core_for_fingerprint`** → `engines/shared/.../settings_fingerprint_core.py` 中的忽略表（再由 **`StrategyRunFingerprint.extract_settings_core`** 调用）

字段含义可参考 `userspace/strategies/settings_example.py` 与 `StrategySettings` 各子数据类。

---

## 规范形态（API / 数据库快照）

工作台 API 与数据库快照须使用同一规范化结果：

- `StrategySettings(raw_settings=...).validate()`
- `StrategySettings.to_dict()`

以此为准；兼容旧数据时可解析 `meta`，持久化以校验后的结构为准。

---

## 工作台指纹：按配置块（推荐默认）

**「剔除」** = 不参与 **`settings_core`** 的哈希（不视为改变「同一策略、同一回测输入」）。  
**「参与」** = 参与哈希。

### 根级 / Meta（对应 `settings_example` 第 1 节及 `meta` 展开）

| 字段 | 策略 |
|------|------|
| **`name`** | **推荐参与**。标识策略配置；若约定「仅以路由上的 `strategy_name` 为准」且不希望改名触发指纹，可在实现中固定为 **剔除**（须在 BED 一处写明注释）。 |
| **`description`** | **剔除**（仅展示与说明文案）。 |
| **`is_enabled`** | **剔除**（是否启用不改变回测数值）。 |
| **`core`** | **整对象参与**（策略私有参数）。 |

### `data`（第 3 节）

| 字段 | 策略 |
|------|------|
| **`base_required_data`**（含 `params.term`、`adjust` 等） | **参与** |
| **`extra_required_data_sources`** | **参与** |
| **`min_required_records`** | **参与** |
| **`indicators`** | **参与** |

### `sampling`（第 4 节）

| 字段 | 策略 |
|------|------|
| **整块** | **参与**（采样策略、`sampling_amount`、各子策略专有字段等会影响股票集合或随机性时须一致）。 |

### `goal`（第 5 节）

| 字段 | 策略 |
|------|------|
| **整块** | **参与**（止盈止损、持仓窗口等影响模拟结果）。 |

### `fees`（第 7 节根级）

| 字段 | 策略 |
|------|------|
| **整块** | **参与**（费率影响资金与成交成本）。 |

### `enumerator`（第 6 节）

| 字段 | 策略 |
|------|------|
| **`use_sampling`** | **参与**（`test/` 与 `output/`；若工作台已统一「全链路采样开关」，实现上勿与价格/资金两处重复矛盾）。 |
| **`max_test_versions`** | **剔除**（仅磁盘保留个数，不改变单次计算结果）。 |
| **`max_output_versions`** | **剔除** |
| **`max_workers`** | **剔除**（并发与性能） |
| **`is_verbose`** | **剔除** |
| **`memory_budget_mb`** | **剔除** |
| **`warmup_batch_size` / `min_batch_size` / `max_batch_size`** | **剔除** |
| **`monitor_interval`** | **剔除** |

与代码对应：`settings_fingerprint_core.py` 中的 **`IGNORE_ENUMERATOR_KEYS`**（及同文件其它 `IGNORE_*` / **`DROP_ROOT_BLOCKS`**）。

### `price_simulator`（第 8 节）

| 字段 | 策略 |
|------|------|
| **`use_sampling`** | **参与**（与统一开关策略一致；若已合并为单一字段可只算一次）。 |
| **`base_version`** | **参与**（锁定读取哪一版枚举产物）。 |
| **`start_date` / `end_date`** | **参与**（若与工作台「运行范围」重复，建议 **二选一**：要么只在全局范围里算日期，要么只在 settings 里算，避免重复计入）。 |
| **`fees`**（覆盖） | **参与**（若存在）。 |
| **`max_workers`** | **剔除** |

### `capital_simulator`（第 9 节）

| 字段 | 策略 |
|------|------|
| **`use_sampling`** | **参与** |
| **`base_version`** | **参与** |
| **`initial_capital`** | **参与** |
| **`start_date` / `end_date`** | **参与**（同上，避免与全局范围重复）。 |
| **`allocation`** | **整对象参与** |
| **`fees`**（覆盖） | **参与**（若存在） |
| **`output.save_trades` / `output.save_equity_curve`** | **剔除**（仅是否多落盘日志/曲线文件，默认不改变同一口径下的数值摘要；若产品将输出体量纳入契约再改为参与）。 |
| **`max_workers`** | **剔除**（若配置中存在，与价格侧一致） |

### `scanner`（第 10 节）

| 字段 | 策略 |
|------|------|
| **整块 `scanner`** | **剔除**（扫描流水线与三条模拟器回测相互独立，不改变枚举/价格/资金数值）。除非将来「扫描结果参与模拟」，另立契约。 |

---

## 与实现的关系

指纹路径：**先** `StrategySettings.validate()` + **`to_dict()`**（默认补足），**再** `strip_fingerprint_non_core`（见 `settings_fingerprint_core.py`）。`StrategyRunFingerprint.extract_settings_core` 仅封装 **`StrategySettings.build_settings_core_for_fingerprint`**；`EnumeratorFingerprint` 为同类型的历史别名。

还会：

- 去掉 **`meta`** 根块（若仍嵌在结构中）
- 去掉 **`IGNORE_ROOT_KEYS`**（如 `description`、`is_enabled`）
- 整块去掉 **`scanner`**（`DROP_ROOT_BLOCKS`）
- 按 **是否启用 sampling** 决定是否保留 **`sampling`** 块（`resolve_sampling_is_used`，与旧版 `enumerator` / 模拟器内开关兼容）
- 按忽略表去掉 **enumerator / price_simulator / capital_simulator** 中非语义键

工作台的 **`settings_core`** 应与上表 **语义一致**；单测应对齐 **`StrategySettings.build_settings_core_for_fingerprint`** / **`strip_fingerprint_non_core`** 与本文。

---

## 仅枚举器（历史）简表

以下块 **参与** 枚举器结果语义哈希：**`core`、`data`、`goal`、`sampling`（按规则裁剪）、`fees`、`enumerator.use_sampling`** 及模拟器内 **非运行时** 字段。**`meta` 展示类字段、enumerator 性能类键** 不参与。

---

## 附注

- 任意 **剔除 / 参与** 规则变更视为 **指纹语义变更**：须递增 [`workbench-version-fingerprint.md`](./workbench-version-fingerprint.md) 中载荷的 **`v`**，或写入变更说明。
- 快照表持久化字段可与 **`enum_fingerprint_id` / `enum_scope_fingerprint_id`** 并存；新增 **`workbench_version_fingerprint_id`** 以工作台专篇文档为准。
- 枚举输出目录中的 **`0_metadata.json` / `0_fingerprint.json`** 仍用于调试与对齐。

---

## 变更记录

| 日期 | 说明 |
|------|------|
| （更新） | 按 `settings_example.py` 与数据类补充逐字段表；明确 `scanner` 整块剔除、enumerator 保留项与运行时剔除项。 |
