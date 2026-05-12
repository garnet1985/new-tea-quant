# 工作台版本指纹

本文说明：**如何用一组确定性因子标识「策略工作台一行快照 / 一次可复现回测」**，用于：

- 判断「当前 settings + 范围」是否对应 **已有版本**（用户无意改回旧配置时可对齐）；
- 与 `sys_strategy_workbench_snapshot` 中持久化的指纹字段配合查询（表结构与仓储实现另述）。

**适用范围**：领域契约与设计约定；**不包含** BFF 路由或前端展示字段命名。

**与其它文档的关系**：

- [`settings-fingerprint-policy.md`](./settings-fingerprint-policy.md)：API settings 形态与 **哪些字段参与 `settings_core` 哈希**。
- [`db-cache-service.md`](./db-cache-service.md)：表级 **`settings_finger_print_id` / `env_fingerprint_id`** 的职责拆分、**命中须两条指纹 AND**、失效与写入语义（实现时的运行时契约）。
- 本文：**工作台版本身份** 的因子（含范围、引擎版本、代码身份等）。

---

## 1. 设计原则

1. **同一指纹 ⇒ 同一套输入契约**：在必填因子齐全时，应指向同一类计算结果；若引擎仍存在非确定性，须在引擎层约束，或由「强制刷新」兜底。
2. **因子分层**：**参数域**（settings 中影响数值的项）、**运行范围域**（股票、时间窗、采样/全量模式）、**计算与环境域**（核心版本号、策略代码身份）。
3. **显式载荷版本**：指纹载荷中带 `"v": <int>`，便于日后更换剔除规则或加盐时迁移。
4. **强制刷新**：请求 **`force_refresh`** 时 **跳过指纹命中**，始终完整重算（不改变指纹定义本身）。

---

## 2. 身份因子（必填维度）

| 因子 | 说明 | 数据来源约定 |
|------|------|----------------|
| **核心 settings** | 去掉不参与回测结果的字段后的规范化对象（`settings_core`） | 前端 API 形态 → BED 规范化与校验 → 再按策略文档剔除（见 [`settings-fingerprint-policy.md`](./settings-fingerprint-policy.md)） |
| **股票列表** | 本次运行实际使用的标的集合 | 规范化：排序、去重、统一代码格式；若以采样展开后的列表为准，须在契约中写明（建议与枚举器实际使用列表一致） |
| **回测时间段** | 起始日、结束日 | 与三步链路共用的一套解析结果（含默认值展开后的最终字符串） |
| **采样 / 全量（运行模式）** | 统一开关：全流程走采样（如 `test/`）或全流程全量（如 `output/`） | 建议单一来源（例如写回 settings 的字段，或单独 **`run_mode`**），避免多处 `use_sampling` 不一致 |
| **核心（引擎）版本** | 影响数值或路径的策略模块 / 核心代码版本号 | 例如 `core/modules/strategy/module_info.yaml` 中的 **`version`**，或仓库约定的 **`CORE_SEMVER`**；仅在破坏性变更时递增 |
| **策略代码身份** | 用户空间策略包 / worker 代码变更 | 见 **§3** |

可选因子（若产品仍依赖行情契约一致性）：

| 因子 | 说明 |
|------|------|
| **数据契约 mapping 指纹** | `data_contract_mapping`：core / userspace `mapping.py` 变更时结果可能不同（实现载荷见 `finger_print.env_fingerprint_id`，`v=4`） |

---

## 3. 策略代码身份（如何做指纹）

目标：**未改 JSON、只改策略目录下 `.py` 时，指纹必须变化。**

推荐组合（实现可择一或合并）：

1. **Worker 粒度**：解析即将加载的 **worker 模块路径**，对 **目标文件（及约定的同包依赖文件）** 做 **内容 SHA256**。
2. **策略包粒度**：对 `userspace/strategies/{strategy_name}/` 下参与运行的 **`*.py`**（排除 `__pycache__` 等）按 **固定排序** 拼接字节流后再 **SHA256**（`strategy_bundle_hash`）。
3. **可选**：在 git 工作区可用 **提交或 tree**，无 git 时退回 (2)。

工作台版本行可使用 **`strategy_code_fp`**：**合并 worker 与策略包哈希**，或只存 **`strategy_bundle_hash`**（团队内固定一种，避免双轨）。

---

## 4. 指纹计算方式

1. 组装 **规范载荷**（UTF-8 JSON）：键名固定、**`sort_keys=True`**，`separators=(",", ":")`，与现有 `StrategyRunFingerprint.compute_fingerprint_id` 一致。
2. **`workbench_version_fingerprint_id = sha256(规范载荷).hexdigest()`**（若改用更短编码须在契约中声明）。
3. **持久化**：快照表可存 **`workbench_version_fingerprint_id`**；若与历史 **`enum_fingerprint_id` / `enum_scope_fingerprint_id`** 并存，须在迁移说明中约定 **以谁为准**。

示例载荷形状（字段名可按实现微调，但必须带版本号）：

```json
{
  "v": 1,
  "strategy_name": "<string>",
  "settings_core": {},
  "stock_ids": ["..."],
  "start_date": "<string>",
  "end_date": "<string>",
  "run_mode": "sampling|full",
  "engine_version": "<semver>",
  "strategy_code_fp": "<hex>",
  "data_contract_mapping": "<optional string>"
}
```

---

## 5. 运行模式与核心参数

- **采样 vs 全量** 决定股票池与目录语义（`test` / `output`），属于 **身份的一部分**。
- 与「仅改描述文案」不同，**必须进入指纹**；实现上可写入 **`settings_core`**（若统一开关写回 settings），或单独 **`run_mode`**（**勿重复计算两次**）。

---

## 6. 强制刷新

- 请求 **`force_refresh: true`**：**不参与指纹命中**，走完整计算路径。
- 用于排障、不信任命中结果、或指纹尚未覆盖的边界情况。

---

## 7. `settings_core` 剔除规则

逐字段 **参与 / 剔除** 已写在 [**`settings-fingerprint-policy.md`**](./settings-fingerprint-policy.md)（按 `settings_example.py` 与数据类对齐）。

实现若合并为单一函数 **`StrategySettings.build_settings_core_for_fingerprint`** / `settings_fingerprint_core.strip_fingerprint_non_core`，应与该表及现有的 **`StrategyRunFingerprint.extract_settings_core`** **用单测对齐**。

更新剔除规则时：递增 **§4** 载荷中的 **`"v"`**，或写入变更说明，避免静默改变命中行为。

---

## 8. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-05 | 增加与 [`db-cache-service.md`](./db-cache-service.md) 的交叉引用：表上 **env_fp** 对应「§2 中除 settings 语义核外的因子」打包。 |
| （初稿） | 因子维度、代码指纹思路、规范哈希、强制刷新。 |
| （更新） | `settings_core` 规则改引用策略专篇；剔除列表以 `settings-fingerprint-policy.md` 为准。 |
