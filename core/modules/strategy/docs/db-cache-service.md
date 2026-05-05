# 策略 DB 缓存服务（DbCache）

本文是 **策略模块内、持久化在 `sys_strategy_workbench_snapshot` 表上的快照缓存** 的权威说明：目标、数据模型、指纹语义、命中规则、失效与清理、对上游 API 的期望，以及实现约束。  
**范围**：后端策略域与表结构；**不** 描述 BFF/前端（产品可对其「缓存不感知」）。

与下列文档配套阅读（本文不重复逐字段表，只固定**职责边界与运行时语义**）：

- [`settings-fingerprint-policy.md`](./settings-fingerprint-policy.md)：settings 规范化形态、哪些字段参与 **settings 语义核**（historically `settings_core`）。
- [`workbench-version-fingerprint.md`](./workbench-version-fingerprint.md)：工作台版本身份因子全集（含 **settings 语义核以外的环境与运行因子**）。

**包布局**（`core/modules/strategy/services/cache/simulator_res_db_cache/`，便于找实现）：

| 子路径 | 职责 |
|--------|------|
| `simulator_res_db_cache.py` | 对外三门面：`write_cache` / `read_cache` / `apply_cache` |
| `orchestration/` | 步骤内可调用的实现：`write/resolve_*`、`apply/paths` 等（编排顺序在 ``simulator_res_db_cache.py``） |
| `service.py` / `config.py` | `DbCacheService` 协调与常量 |
| `persistence/` | 表级读写（`snapshot_persist`：枚举与通用 patch） |
| `domain/` | 工作台快照领域（版本列表、对比、恢复；无双指纹命中逻辑） |
| `runtime/` | 枚举器 CLI/BFF 运行期组装与指纹 ID |
| `settings/` | `StrategySettingsService`（API ↔ runtime） |
| `audit/` | `result_summary` 行级 `write_count` 审计 |
| `finger_print/` | 列指纹与运行期 `StrategyRunFingerprint` |
| `enumerator/` | 枚举载荷与 DB 可存格式变换 |

---

## 1. 业务目标

- **缓存三类模拟器的摘要结果**：策略模块内的 **枚举回测器**、**价格因素回测器**、**资金回测器**。三者各自在模拟完成后产生 **summary**（JSON，结构可不同）。
- **同一逻辑行**上聚合三步结果：表里 **`result_summary`** 为 JSON，约定形如 **三键**（名称以实现为准，须与代码一致），例如：

```json
{
  "enum": { "...": "枚举器 result_summary" },
  "price_factor": null,
  "capital_allocation": null
}
```

- **三步不会在一次任务里全部跑完**：通常 **逐个回测**；缓存写入发生在 **某一步 job 成功结束且无错误** 之后，由外部调用 DbCache 提供的接口写入（或更新）对应键。**指纹生成不依赖**「三步是否已齐全」——只要本次写入所用的 settings 与环境上下文一致，指纹应与「仅跑完枚举」时一致（除非 env 因子中包含「已完成步骤」类产品字段；当前约定 **不包含**，详见下文）。

---

## 2. 表与字段（`sys_strategy_workbench_snapshot`）

表定义见：`core/tables/ui_bff/strategy_workbench_snapshot/schema.py`，Model：`model.py`。

核心列语义：

| 列 | 含义 |
|----|------|
| `id` | 表主键（自增 bigint）。 |
| `strategy_name` | 策略目录名。 |
| `version` | **策略维度内自增**的人类可读版本号（展示为 v1、v2…）。**不是**表的业务主键的唯一维度；与 `strategy_name` 组成唯一约束 `uk_swb_snapshot_strategy_version`。领域侧也常称此为 **snapshot_id**（与 model 注释一致）。 |
| `settings_snapshot` | 该版本对应的 **完整 settings 快照**（JSON），来源可为前端规范化结果或 userspace，但入库前须经 **`StrategySettings` 数据类规范化** 后为统一形状（见 §5）。 |
| `result_summary` | 三步聚合摘要（JSON），见 §1。 |
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

三者 **一一对应同一快照版本**：一行记录代表「某策略、某 version、某组 settings 快照、某组 (settings_fp, env_fp)、聚合后的 result_summary」。

---

## 4. 缓存命中（必读）

**命中条件**：在同一 `strategy_name` 下，**`settings_finger_print_id` 与 `env_fingerprint_id` 必须同时与查找条件相等（逻辑 AND）**，才算命中该快照行。

**禁止**：使用「仅 settings_fp 或仅 env_fp 任一相等」作为命中（历史上 Model 层若存在 OR 语义，与产品定义冲突，应在 DbCache / Model 修正为 AND）。

**version**：仅用于展示与按版本读写；**不作为**指纹命中的替代条件。

---

## 5. 职责边界（已定）

| 组件 | 职责 |
|------|------|
| **Strategy flow / 各回测器** | 负责跑出 **result_summary**；模拟完成后在 **无错误** 的前提下调用 DbCache 暴露的接口触发缓存写入；**不**负责拼指纹载荷细节（除非向 DbCache 传入运行上下文对象以便生成器采集）。 |
| **`StrategySettings` 数据类** | 提供 **标准 settings**：`validate` + `to_dict()` 等与契约一致的快照；**不提供**指纹专用入口方法（指纹逻辑不在 settings 包）。 |
| **指纹生成（实现置于 `services/cache/simulator_res_db_cache/` 包内）** | **全部**指纹相关算法（语义剔除、settings_fp、env_fp 载荷与哈希）均属 DbCache 的 **内部能力**；其它模块 **不应** 为「产出可发布的缓存键」而直接调用指纹子模块，以免流程分叉不可控。对外仅通过 **DbCache 服务 API** 使用缓存能力。 |
| **DbCache 服务** | **协调**：接收上游传入的原始 settings（或序列化对象）、运行上下文；内部调用 `StrategySettings` 规范化 → 调用内部指纹生成器生成 **settings_fp + env_fp** → 按 §6、§7 读写表。**DbCache 不负责「代替」回测器计算 summary**，只负责 **缓存命中判断与持久化调度**。 |

---

## 6. 单行生命周期与 `result_summary` 写入规则

- **分步跑**：允许先有 `enum` 再有 `price_factor`、`capital_allocation`。
- **写入策略**：命中缓存后的更新（或同指纹行的增量写入）为 **直接覆盖** **`result_summary` 中与本次模拟器对应的那一个键**，**不做深度 merge**；其它键保留上一状态。
- **允许写入缓存的前提**：对应模拟器 **job 完成且无错误**（由调用方保证）；DbCache 不写失败任务的摘要。

指纹在行更新时 **不因「只填了 enum」而改变**，除非 settings 或 env 因子实际发生变化。

---

## 7. 失效、清理与强制刷新

下列规则中的 **数值均为可配置常量**（文档中用 **n、m、T** 表示；当前讨论过的默认值：单行最多 **n=10** 次更新、每策略最多 **m=50** 行版本、**T=24 小时**未更新视为过期）。

1. **时间（热度）**：距 **`updated_at`** 超过 **T** 的记录视为过期：**不得命中**；实现上应先保证 **不使用该缓存**（可先删行或命中时再删，以简单为准）；后续可迁移到定时任务统一清理。
2. **每策略版本个数上限**：每个 `strategy_name` 最多保留 **m** 条版本行；当出现第 **m+1** 条新版本需求时，**删除最早版本**（以实现定义的「最早」为准，通常最低 `version` 或最旧 `updated_at`），再写入新版本。
3. **单行复写次数**：若同一缓存行累计 **UPDATE**（每次持久化算一次写入）超过 **n** 次，则触发删除或整行重建策略（实现择简：删记录再插入或清空内容再写，以 IO 小为准）。  
   **实现（已定）**：不在表上新增列；在 **`result_summary` JSON** 内保留元键 **`_db_cache_meta`**（与各模拟器业务键隔离），其中 **`write_count`** 为累计写入次数；新建行置为 1，每次合并更新前递增；超过 **`MAX_SNAPSHOT_ROW_UPDATES`**（默认 **10**，见 ``core/modules/strategy/services/cache/simulator_res_db_cache/config.py``）则 **DELETE** 该行。枚举等持久化路径在删行后 **按当前指纹与 settings 快照再 INSERT**（见 ``audit/result_summary_audit.py``、``persistence/snapshot_persist.py``）。领域 **`StrategyWorkbenchSnapshotService`** 新建仅 settings 的快照行时同样写入初始 **`write_count`**，避免「只有枚举路径才有审计」的分叉。
4. **`force_refresh`**：调用方显式要求 **忽略缓存命中**、强制完整重算；完成后 **重写**缓存。被跳过的那一行命中记录应 **删除或作废**，避免后续误用（删整条或等价标记均可，择简）。

**说明**：短期可在读写路径内联清理；长期可将过期扫描迁入 **cron job**，但语义不变：**过期资源不得作为有效命中**。

---

## 8. 对外 API 形状（方向约定）

- 上游 **仅通过 DbCache 暴露的少量公共方法** 访问缓存（名称以实现为准）。
- **对外编排入口（目标形态）**：``simulator_res_db_cache.write_cache``（``simulator_res_db_cache.py``）仅暴露 ``simulator_name``、``strategy_name``、``raw_settings``、``result_summary_patch``、``force_refresh``、``workbench_run_id``；**股票列表、env 用起止日（``sampling`` 空则按运行时 fallback，不写回用户 settings）、run_mode、系统版本（``core.system.get_version()``）、worker 锚点、data_contract_mapping** 均在编排层内部解析后再调用 ``DbCacheService.generate_cache``。
- **协调实现（当前）**：`DbCacheService.generate_cache(...)`（``service.py``）在规范化 settings、生成 **settings_fp + env_fp** 后，按 **`simulator_name`** 分支：**枚举** → ``persist_enum_snapshot``；**价格 / 资金** → ``persist_simulator_summary_patch``（写入 ``price_factor`` / ``capital_allocation`` 键）。  
  - **`result_summary_patch`**：枚举器为 **单行** 摘要 dict 或含 **`"enum"`** 的外层 dict；价格 / 资金为 **该键对应摘要 dict**，或外层包含 **`"price_factor"`** / **`"capital_allocation"`** 时取该键。  
  - **`force_refresh`**：枚举 → ``replace_enum_cache_by_fingerprints``；价格 / 资金 → ``strip_result_summary_keys_by_fingerprints`` 仅去掉对应顶层键（保留指纹列），均带写次数审计后再写入。
- **规范化 settings**：由 **DbCache 内部**调用 `StrategySettings` 完成，确保指纹与快照同源、可追溯。

---

## 9. 实现注意（避免下一任重复踩坑）

1. **命中查询**：必须 **`strategy_name + settings_fp + env_fp` 三条件 AND**，参见 §4。  
2. **指纹模块位置**：语义剔除与哈希实现位于 **`core/modules/strategy/services/cache/simulator_res_db_cache/`**（可多文件）；**不得**在 `StrategySettings` 数据类包内保留指纹剔除表。  
3. **finger_print 子包**：``core`` / ``semantic_core_strip`` 服务 Db 列指纹；``run_types``（``StrategyRunFingerprint``）与 ``run_service``（Manager / RuntimeService）为运行期业务层，与核心层同目录；``services/fingerprint`` 仅为兼容转发。  
4. **文档与代码漂移**：若调整剔除规则或 env 载荷版本，须同步 [`settings-fingerprint-policy.md`](./settings-fingerprint-policy.md)、[`workbench-version-fingerprint.md`](./workbench-version-fingerprint.md) 中的 **`v` 或变更说明**，避免静默改变命中行为。

---

## 10. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-05 | 初稿：汇集 DbCache 目标、表语义、双指纹 AND 命中、职责边界、分步 summary、四类失效 + force_refresh、对外 API 方向、实现约束。 |
| 2026-05 | 实现起步：`SysStrategyWorkbenchSnapshotModel.list_by_strategy_fingerprints` 双指纹 **AND**；`env_fingerprint_id` 载荷 **v=3**（不再嵌入 `settings_core`）；`DbCacheService`（TTL 命中、版本数裁剪）；`config.py` 常量。 |
| 2026-05 | 单行复写次数：``result_summary`` 内 ``_db_cache_meta.write_count``、``audit/result_summary_audit`` + `MAX_SNAPSHOT_ROW_UPDATES`；超限时删行并在各持久化路径上按指纹重建；`Model` 层去除未再使用的 ``clear_enum_cache_for_snapshot_id`` / ``replace_enum_cache_by_fingerprints``；`DbCacheService.generate_cache` 已对接枚举 `persist_enum_snapshot`（`force_refresh` 先 ``replace_enum_cache_by_fingerprints``）。 |
| 2026-05 | ``persist_simulator_summary_patch`` / ``strip_result_summary_keys_by_fingerprints``；`generate_cache` 支持 **price_factor**、**capital_allocation**，``force_refresh`` 按模拟器分支剥离键。 |
| 2026-05 | 对外编排骨架 ``simulator_res_db_cache.write_cache``：收窄入参；env 侧日期/版本/worker/data_contract/股票列表由内部解析（见 §8）。 |
