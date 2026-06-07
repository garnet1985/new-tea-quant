# 策略 DB 缓存服务（DbCache）

本文是 **策略模块内、持久化在 `sys_strategy_workbench_snapshot` 表上的快照缓存** 的权威说明：目标、数据模型、指纹语义、命中规则、失效与清理、对上游 API 的期望，以及实现约束。  
**范围**：后端策略域与表结构；**不** 描述 BFF/前端（产品可对其「缓存不感知」）。

与下列文档配套阅读（本文不重复逐字段表，只固定**职责边界与运行时语义**）：

- [`settings-fingerprint-policy.md`](./settings-fingerprint-policy.md)：settings 规范化形态、哪些字段参与 **settings 语义核**（historically `settings_core`）。
- [`workbench-version-fingerprint.md`](./workbench-version-fingerprint.md)：工作台版本身份因子全集（含 **settings 语义核以外的环境与运行因子**）。

**包布局**（`core/modules/strategy/services/cache/simulator_res_db_cache/`，便于找实现）：

| 子路径 | 职责 |
|--------|------|
| `facade.py` | `read_cache` / `write_cache`（解析指纹后读表或写入） |
| `cache_service.py` / `config.py` | `SimulatorResDbCacheService`（含表访问私有方法：枚举 lookup、槽位写入）、常量 |
| `domain/` | `StrategyWorkbenchSnapshotService`：`v{n}` ↔ snapshot_id（展示用） |
| `runtime/` | 枚举器 CLI/BFF 运行期组装与指纹 ID |
| `settings/` | `StrategySettingsService`（API ↔ runtime） |
| `audit/` | `result_report_audit`：``result_report`` 行级 `write_count` 审计 |
| `finger_print/` | 列指纹与运行期 `StrategyRunFingerprint` |
| `enumerator/` | 枚举载荷与 DB 可存格式变换 |

---

## 1. 业务目标

- **缓存三类模拟器的摘要结果**：策略模块内的 **枚举回测器**、**价格因素回测器**、**资金回测器**。三者各自在模拟完成后产生 **summary**（JSON，结构可不同）。
- **同一逻辑行**上聚合三步结果：表里 **`result_report`** 为 JSON，约定形如 **三键**（名称以实现为准，须与代码一致），例如：

```json
{
  "enum": { "...": "枚举器 result_report" },
  "price_factor": null,
  "capital_allocation": null
}
```

- **三步不会在一次任务里全部跑完**：通常 **逐个回测**；缓存写入发生在 **某一步 job 成功结束且无错误** 之后，由外部调用 DbCache 提供的接口写入（或更新）对应键。**指纹生成不依赖**「三步是否已齐全」——只要本次写入所用的 settings 与环境上下文一致，指纹应与「仅跑完枚举」时一致（除非 env 因子中包含「已完成步骤」类产品字段；当前约定 **不包含**，详见下文）。

---

## 2. 表与字段（`sys_strategy_workbench_snapshot`）

表定义见：`core/tables/strategy_workbench_snapshot/schema.py`，Model：`model.py`（与 BFF 共用，核心模块不依赖 `ui_bff` 路径）。

核心列语义：

| 列 | 含义 |
|----|------|
| `id` | 表主键（自增 bigint）。 |
| `strategy_name` | 策略目录名。 |
| `version` | **策略维度内自增**的人类可读版本号（展示为 v1、v2…）。**不是**表的业务主键的唯一维度；与 `strategy_name` 组成唯一约束 `uk_swb_snapshot_strategy_version`。领域侧也常称此为 **snapshot_id**（与 model 注释一致）。 |
| `settings_snapshot` | 该版本对应的 **完整 settings 快照**（JSON），来源可为前端规范化结果或 userspace，但入库前须经 **`StrategySettings` 数据类规范化** 后为统一形状（见 §5）。 |
| `result_report` | 三步聚合摘要（JSON），见 §1。 |
| `settings_finger_print_id` | **settings 语义核**导出的稳定指纹（hex，长度以实现为准）。 |
| `env_fingerprint_id` | **除 settings 语义核以外的身份因子**（见 [`workbench-version-fingerprint.md`](./workbench-version-fingerprint.md) §2）打包哈希得到的指纹。 |
| `created_at` / `updated_at` | 创建时间与 **最后更新时间（热度）**；失效规则 §7 依赖 `updated_at`。 |

索引包含 `(strategy_name, settings_finger_print_id)`、`(strategy_name, env_fingerprint_id)` 等；**缓存命中查询必须以「策略名 + 两条指纹」同时相等为准**（见 §4）。

---

## 3. 三个编号：`version`、settings_fp、env_fp

- **`version`**：**可读版本**，按 `strategy_name` **单独递增**（策略 A 的 v1、v2 与策略 B 的 v1、v2 无关）。**不信任**外部传入的 version 作为缓存校验依据；校验缓存必须以指纹为准。
- **`settings_finger_print_id`（以下简称 settings_fp）**：对 **settings 语义核**做规范载荷后哈希（剔除不参与数值契约的字段，规则见 `settings-fingerprint-policy.md`；实现上经 `StrategySettings` 校验后的快照再走语义剔除）。
- **`env_fingerprint_id`（以下简称 env_fp）**：对 **`workbench-version-fingerprint.md` §2 所列因子中，除去已反映在 settings 语义核内的部分之后**，其余 **环境与运行身份因子** 组装规范载荷再哈希。  
  **已定口径**：env_fp =「§2 身份因子」里 **除 settings_core（语义核）以外** 的外部因素打包哈希（股票列表、回测区间、运行模式、引擎版本、策略代码身份、`data_contract_mapping` 等——具体字段以实现载荷为准，须与文档 §2 对齐且不重复计算已在语义核中的键）。

三者 **一一对应同一快照版本**：一行记录代表「某策略、某 version、某组 settings 快照、某组 (settings_fp, env_fp)、聚合后的 result_report」。

---

## 4. 缓存命中（必读）

**命中条件**：在同一 `strategy_name` 下，**`settings_finger_print_id` 与 `env_fingerprint_id` 必须同时与查找条件相等（逻辑 AND）**，才算命中该快照行。

**禁止**：使用「仅 settings_fp 或仅 env_fp 任一相等」作为命中（历史上 Model 层若存在 OR 语义，与产品定义冲突，应在 DbCache / Model 修正为 AND）。

**version**：仅用于展示与按版本读写；**不作为**指纹命中的替代条件。

**读路径（当前实现）**：``lookup_enum_cache`` 在双指纹 AND 命中后，仅读取该行 **`result_report.enum`**（见 §6.1）；**不**跨兄弟行、**不**从 `price_factor` 推断；**不**再按 `updated_at` 做时间窗过滤；若产品仍需 §7 的时间失效，应在离线清理或写入侧处理。

---

## 5. 职责边界（已定）

| 组件 | 职责 |
|------|------|
| **Strategy flow / 各回测器** | 负责跑出 **result_report**；模拟完成后在 **无错误** 的前提下调用 DbCache 暴露的接口触发缓存写入；**不**负责拼指纹载荷细节（除非向 DbCache 传入运行上下文对象以便生成器采集）。 |
| **`StrategySettings` 数据类** | 提供 **标准 settings**：`validate` + `to_dict()` 等与契约一致的快照；**不提供**指纹专用入口方法（指纹逻辑不在 settings 包）。 |
| **指纹生成（实现置于 `services/cache/simulator_res_db_cache/` 包内）** | **全部**指纹相关算法（语义剔除、settings_fp、env_fp 载荷与哈希）均属 DbCache 的 **内部能力**；其它模块 **不应** 为「产出可发布的缓存键」而直接调用指纹子模块，以免流程分叉不可控。对外仅通过 **DbCache 服务 API** 使用缓存能力。 |
| **DbCache 服务** | **协调**：接收上游传入的原始 settings（或序列化对象）、运行上下文；内部调用 `StrategySettings` 规范化 → 调用内部指纹生成器生成 **settings_fp + env_fp** → 按 §6、§7 读写表。**DbCache 不负责「代替」回测器计算 summary**，只负责 **缓存命中判断与持久化调度**。 |

---

## 6. 单行生命周期与 `result_report` 写入规则

- **分步跑**：允许先有 `enum` 再有 `price_factor`、`capital_allocation`。
- **写入策略**：命中缓存后的更新（或同指纹行的增量写入）为 **直接覆盖** **`result_report` 中与本次模拟器对应的那一个键**，**不做深度 merge**；其它键保留上一状态。
- **允许写入缓存的前提**：对应模拟器 **job 完成且无错误**（由调用方保证）；DbCache 不写失败任务的摘要。

指纹在行更新时 **不因「只填了 enum」而改变**，除非 settings 或 env 因子实际发生变化。

**同一 `(settings_fp, env_fp)` 下**：三步依次落库只会 **反复 merge 同一 `version` 行**；**不得**因累计写入次数而删行并分配新 `version`（见 §6.1、§7）。

---

## 6.1 三槽位契约与读路径（禁止自动修补）

本节是工作台 **「有就是有、没有就是没有」** 的权威约定：UI / 报告 API **只展示** DB 快照行里各步骤**自己写入**的槽位；**禁止**用其它槽位或兄弟行去「补全」缺失数据。

### 6.1.1 指纹 ↔ 版本行

| 事件 | 行为 |
|------|------|
| **`settings_fp` 或 `env_fp` 任一变化** | **新建**快照行 → 新的 `version`（v1、v2… 递增） |
| **双指纹均与已有行相同** | **命中同一行**，按步骤 merge 对应槽位，**不**新建 `version` |
| **仅跑完其中一步** | 允许该行暂时只有部分槽位（例如仅有 `enum`） |

**禁止**：用「仅 `settings_fp` 相同」或「兄弟 `version` 上有 enum」去命中/合并另一指纹行；缓存查找与 `set_cache` 目标行解析均为 **`strategy_name + settings_fp + env_fp` 三条件 AND**。

### 6.1.2 谁写哪个槽（写侧唯一来源）

| 模拟器（`Simulator`） | `result_report` 键 | 写入入口（实现） |
|----------------------|-------------------|------------------|
| 枚举回测器 | `enum` | `persist_enum_snapshot`（枚举 job 成功后） |
| 价格因素回测器 | `price_factor` | `persist_price_factor_snapshot` |
| 资金回测器 | `capital_allocation` | `persist_capital_allocation_snapshot` |

- **每一步只写自己的槽**；其它键保持上一状态或为空。
- **`price_factor` 内可含 `output_version.enumerator_output_dir`**：表示**本价格回测所依赖的枚举磁盘目录**（运行血缘元数据），**不等于** `enum` 槽已落库。
- **禁止的写侧行为**（曾导致 opportunities 从 140 刷成 23206 等错乱，已移除）：
  - 价格步落库时 **不得** 向同行注入 `enum` 路径 stub（原 `_maybe_merge_enum_path_stub`）。
  - 价格步落库时 **不得** 向同行注入 `capital_allocation` 路径 stub。
  - 资金步落库时 **不得** 根据 `price_factor` 反推并写入 `enum` 槽。

若某行 **仅有 `price_factor`、没有 `enum`**：视为 **落库/流程 bug**，应由修复枚举步或持久化链路解决，**不在读路径掩盖**。

### 6.1.3 DB 摘要 vs 磁盘明细

| 层级 | 存放位置 | 内容 |
|------|----------|------|
| **步骤摘要** | `result_report` 对应槽位（DB JSON） | `enumMetrics`、`initial_capital`、曲线标签等**汇总指标**；可经 `compact_*_for_cache` 去掉逐股大块，但**摘要字段应可独立展示** |
| **逐股 / 大块明细** | `userspace/strategies/{name}/results/simulations/{enum\|price\|capital}/<dir>/` | 如 `0_stock_ref.json`、单股 K 线依赖文件等 |

**读时 hydrate**（`hydrate_enum_slot` / `hydrate_capital_slot` / `hydrate_workbench_result_report`）：在槽位**已存在**且内含相对路径或已存摘要时，从磁盘 **补全** 展示字段。**这不是**跨槽推断——槽位为空则 hydrate 无输入，结果为空。

物理文件缺失：与 **V2-07 `report_ref`** 一致，由 **UI 提示用户对该步重新 run**；服务端 **不** 从 `price_factor` 猜枚举目录。

### 6.1.4 读路径（报告 API、latest、按 version、指纹 lookup）

实现落点：`workbench.py`（`fetch_workbench_by_version`、`_resolve_*_report_slot`）、`snapshot_slot_adapters.lookup_*_cache`、`SimulatorResDbCacheService.load_cache_by_fingerprints`。

**规则**：

1. 只读 **当前请求所指定快照行**（或双指纹 AND 命中的那一行）上的 `enum` / `price_factor` / `capital_allocation`。
2. **不得** 读取 `price_factor.output_version.enumerator_output_dir` 来构造 enum 报告。
3. **不得** 在同 `settings_fp` 的其它 `version` 兄弟行上查找 `enum` 并覆盖当前行展示（原 `resolve_enum_slot_for_fingerprints` 兄弟行逻辑已移除）。
4. **不得** 从 price 目录反查 capital 并假装当前行已有 `capital_allocation`。
5. 槽位缺失 → API / `result_report` 中该步为 **空**；FED 按步骤状态显示「未运行」或「数据异常」，**不** 静默填数。

**与 UI 的对应关系**：

- 执行面板 opportunities 等标量：来自 **当前 `version_id` 行** 的 `enum` 槽（经 hydrate 后的 `enumMetrics` / `opportunities`），**不是** price 元数据。
- **V2-07**：`step=enum` 时 `report` 仅来自该行 `enum` 槽；无槽 → 空 `report` 或 404（以实现为准，但**不得** fallback 到 price 引用的旧 enum 目录）。

### 6.1.5 `_db_cache_meta.write_count`

- 仍在每次 merge 前递增，供审计与排障。
- **仅统计**，**不** 触发删行、**不** 分配新 `version`（原 `MAX_SNAPSHOT_ROW_UPDATES` 轮转已废弃，见 §7）。

---

## 7. 失效、清理与强制刷新

下列规则中的 **数值均为可配置常量**（文档中用 **m、T** 表示；当前默认值：每策略最多 **m=50** 行版本、**T=24 小时**未更新视为过期）。

1. **时间（热度）**：距 **`updated_at`** 超过 **T** 的记录视为过期：**不得命中**；实现上应先保证 **不使用该缓存**（可先删行或命中时再删，以简单为准）；后续可迁移到定时任务统一清理。
2. **每策略版本个数上限**：每个 `strategy_name` 最多保留 **m** 条版本行；当出现第 **m+1** 条新版本需求时，**删除最早版本**（以实现定义的「最早」为准，通常最低 `version` 或最旧 `updated_at`），再写入新版本。详见 [`retention.md`](./retention.md)。**删 DB 行不删磁盘 output 目录**（可能产生孤儿目录）。
3. **`write_count`（审计）**：`result_report._db_cache_meta.write_count` 记录同行累计 merge 次数；**不改变 `version`**，**不** 因超限删行重建。常量 `MAX_SNAPSHOT_ROW_UPDATES` 保留在 `config.py` 仅为历史兼容，**无运行时轮转语义**。
4. **`force_refresh`**：调用方显式要求 **忽略缓存命中**、强制完整重算；完成后 **重写**缓存。被跳过的那一行命中记录应 **删除或作废**，避免后续误用（删整条或等价标记均可，择简）。

**说明**：短期可在读写路径内联清理；长期可将过期扫描迁入 **cron job**，但语义不变：**过期资源不得作为有效命中**。

---

## 8. 对外 API 形状（方向约定）

- 上游 **仅通过 DbCache 暴露的少量公共方法** 访问缓存（名称以实现为准）。
- **对外编排入口**：``facade.write_cache`` 暴露 ``simulator_name``、``strategy_name``、``raw_settings``、``partial_result_report``、``force_refresh`` 及与 env 相关的显式入参（股票列表、交易日等由 ``resolve_db_cache_fingerprints`` 消费）；内部调用 ``SimulatorResDbCacheService.generate_cache``。
- **协调实现**：`SimulatorResDbCacheService.generate_cache`（``cache_service.py``）在规范化 settings、生成 **settings_fp + env_fp** 后，按 **`simulator_name`** 分支：**枚举** → ``persist_enum_snapshot``；**价格 / 资金** → ``persist_simulator_report_patch``。  
  - **`partial_result_report`**：仅一种入参——本步摘要 dict，与 ``result_report`` 对应槽位 JSON **同形**；**刻意**不接收其它包装/聚合形状（维护成本由调用方保证对齐）。  
  - **`force_refresh`**：枚举 → ``replace_enum_cache_by_fingerprints``；价格 / 资金 → ``strip_result_report_keys_by_fingerprints`` 仅去掉对应顶层键（保留指纹列），均带写次数审计后再写入。
- **规范化 settings**：由 **DbCache 内部**调用 `StrategySettings` 完成，确保指纹与快照同源、可追溯。

---

## 9. 实现注意（避免下一任重复踩坑）

1. **单一契约**：DbCache 对「写入 dict / 表内槽位 JSON」**只实现一种形状**，不做多形态猜测或静默降级；旧形态需在迁移脚本或调用层显式处理，**不在**缓存内核分叉。  
2. **命中查询**：必须 **`strategy_name + settings_fp + env_fp` 三条件 AND**，参见 §4。  
3. **指纹模块位置**：语义剔除与哈希实现位于 **`core/modules/strategy/services/cache/simulator_res_db_cache/`**（可多文件）；**不得**在 `StrategySettings` 数据类包内保留指纹剔除表。  
4. **finger_print 子包**：``core`` / ``semantic_core_strip`` 服务 Db 列指纹；``run_types``（``StrategyRunFingerprint``）与 ``run_service``（Manager / RuntimeService）为运行期业务层，与核心层同目录；``services/fingerprint`` 仅为兼容转发。  
5. **文档与代码漂移**：若调整剔除规则或 env 载荷版本，须同步 [`settings-fingerprint-policy.md`](./settings-fingerprint-policy.md)、[`workbench-version-fingerprint.md`](./workbench-version-fingerprint.md) 中的 **`v` 或变更说明**，避免静默改变命中行为。

---

## 10. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-05 | 初稿：汇集 DbCache 目标、表语义、双指纹 AND 命中、职责边界、分步 summary、四类失效 + force_refresh、对外 API 方向、实现约束。 |
| 2026-05 | 实现起步：`SysStrategyWorkbenchSnapshotModel.list_by_strategy_fingerprints` 双指纹 **AND**；`env_fingerprint_id` 载荷 **v=3**（不再嵌入 `settings_core`）；`DbCacheService`（TTL 命中、版本数裁剪）；`config.py` 常量。 |
| 2026-05 | 单行复写次数：``result_report`` 内 ``_db_cache_meta.write_count``、``audit/result_report_audit`` + `MAX_SNAPSHOT_ROW_UPDATES`；超限时删行并在各持久化路径上按指纹重建；`Model` 层去除未再使用的 ``clear_enum_cache_for_snapshot_id`` / ``replace_enum_cache_by_fingerprints``；`DbCacheService.generate_cache` 已对接枚举 `persist_enum_snapshot`（`force_refresh` 先 ``replace_enum_cache_by_fingerprints``）。 |
| 2026-05 | ``persist_simulator_report_patch`` / ``strip_result_report_keys_by_fingerprints``；`generate_cache` 支持 **price_factor**、**capital_allocation**，``force_refresh`` 按模拟器分支剥离键。 |
| 2026-05 | 对外编排骨架 ``simulator_res_db_cache.write_cache``：收窄入参；env 侧日期/版本/worker/data_contract/股票列表由内部解析（见 §8）。 |
| 2026-06 | **三槽位契约（§6.1）**：移除写侧 enum/capital 路径 stub、读侧 price→enum / 兄弟行 enum / price→capital 自动修补；`version` 仅随指纹变化，**不再**因 `write_count` 超限删行建新 version；UI/报告 **有就是有、没有就是没有**。 |
