# Simulation Versioning Redesign

**状态：** Batch 1–6 已落地（用户盘旧 simulation 目录需按 ``VERSIONING_CLEANUP.md`` 手动清理）  
**范围：** 策略回测产物布局、指纹命中、工作台缓存/发布、CLI↔UI 混用  
**兼容性：** **不考虑**旧布局 / 旧 DB 快照语义；哪里不兼容就改哪里。

---

## 1. 目标（两个）

1. **相同条件再跑 → 立刻复用**已有 version 产物（指纹命中）。
2. **可按 version 对比历史 report**（含归因），配置可恢复、可复现叙事清晰。

非目标：保留「发布策略」、工作台 DB version ≠ 磁盘 version 的双轨、静默覆盖历史。

---

## 2. 已拍板决策

| # | 决策 |
|---|------|
| D1 | 布局：`results/simulations/{version_id}/{enum\|price\|portfolio}/` |
| D2 | 版本索引只在 `results/simulations/meta.json`（`next_version_id` + `registry`） |
| D3 | **一个 version id 跨三步共享**；未跑 step 无产物目录 / 无 `runtime_env.json` |
| D4 | **settings.py 是日常编辑 SOT**；取消「发布到 settings」作为主路径 |
| D5 | **执行与缓存均以 effective settings 的指纹子集为准**，不是物理文件字节 |
| D6 | 指纹主键：`settings_fp` + `env_fp`；退役 `disk_settings_hash` 作为命中键 |
| D7 | 配置快照冻结在 `{vid}/effective_settings.json`；浏览历史 ≠ 静默改 settings.py |
| D8 | 「恢复配置」为显式动作，写回前 round-trip 校验指纹 |
| D9 | env 变了（含 NTQ 版本）：旧 version **环境失效**（不可 cache hit），报告仍可打开 |
| D10 | 对环境失效 version 强跑 → **新建 version**，不覆盖旧目录 |
| D11 | 同 env + 同 settings 下补跑缺失 step → **写在同一 version** 下 |
| D12 | 触顶 keep-N：**不静默删**；拒绝 allocate 或确认后删 |
| D13 | 归因：落在 `{vid}/{step}/analysis/`，与 step 同生共死 |
| D14 | DB 工作台快照：降级或删除；UI 版本列表 = 磁盘 `registry` |

---

## 3. 目标目录树

```text
{strategy}/results/simulations/
  meta.json                    # next_version_id + registry（见下）
  3/
    effective_settings.json    # 本 version 冻结的 effective 指纹子集 + entity_ids
    enum/
      runtime_env.json
      overall_report.json
      entities/...
      analysis/report.json     # 归因（若已跑）
    price/
      ...
    portfolio/
      ...
```

### `simulations/meta.json`

```json
{
  "next_version_id": 4,
  "strategy_name": "demo/regression/rsi/rsi_v1_baseline",
  "last_updated": "...",
  "registry": {
    "1": {
      "created_at": "...",
      "updated_at": "...",
      "settings_fp": "...",
      "env_fp": "..."
    },
    "3": {
      "created_at": "...",
      "settings_fp": "...",
      "env_fp": "...",
      "pinned": true
    }
  }
}
```

约定：

- **registry 的 key 即 version id**，条目内不重复存 `version_id`。
- **指纹平铺**为 `settings_fp` / `env_fp`（不用嵌套 `fingerprints` 对象）。
- **无 `fingerprint_index`**：按双指纹命中时线性扫描 `registry`（version 数量可承受）。
- 条目可扩展：`pinned`、`keep_forever` 等标记与指纹字段并列。

### 两种查 version（等价）

| 入口 | 做法 |
|------|------|
| **vid** | `registry[vid]` 或 `VersionMetaStore.get_registry_entry` |
| **双指纹** | 扫描 registry，匹配 `settings_fp` + `env_fp` |

### `{vid}/effective_settings.json`

- **带 value 的配置快照**（非 registry 索引层）。
- 内容为 `StrategySettings.extract_effective_settings()` 的结果 + `entity_ids`。
- **字段抽取规则**在上层：`StrategySettings.FINGERPRINT_FIELDS`（策略通用）。
- 三步（enum / price / portfolio）**共享**同一文件，写在 `{vid}/` 根下。

### step 是否已有产物

不单独存 steps meta；看磁盘：

```text
{vid}/{step}/runtime_env.json 存在 → 该 step 已跑完
```

---

## 4. 运行时契约（防用户困惑）

| 用户动作 | 系统行为 | 提示要点 |
|----------|----------|----------|
| 打开 version N | 只读报告/归因 | 历史快照 |
| 配置与 N 相同且 env 相同 → Run | 命中 N，复用 | 命中已有版本 N |
| 配置变了 → Run | 新建 N+1 | 新版本 |
| env 变了（含 NTQ）仍打开 N | 可看报告；不可 hit | 该版本在当前环境已失效（`env_invalid`） |
| 对环境失效 N 强跑 | 新建 M，保留 N | 需重新 run；结果在新版本 |
| 在有效 N 上补跑缺失 step | 写入 N/{step} | 同版本补全 |
| 恢复配置到 N | 读 `effective_settings.json`，校验 fp 后写 settings.py | 显式确认 |
| version 触顶 | 拒绝或确认删除 | 不静默 |

主叙事：

> 老版本在当前环境下**环境失效** → 不能复用 → 重跑产生**新版本**；旧报告仍可查看。

**术语（Batch 4+）：**

| 字段 / 文案 | 含义 |
|-------------|------|
| `env_invalid` | registry 存盘 `env_fp` ≠ 当前运行环境指纹；**禁止 cache hit**，报告只读仍可 |
| UI / CLI 提示 | 用「环境已失效」「当前环境不可用」等中文，不用 stale |

---

## 5. 指纹（实施要点）

1. `effective = calculate_effective_settings(disk, runtime)`  
2. `subset = extract_effective_settings(effective)` ← `FINGERPRINT_FIELDS` 子集  
3. `settings_fp = hash(subset ⊕ entity_ids)`（数值 coerce、稳定序列化）  
4. `env_fp = hash(hooks/引擎/DB/合约/period/execution_mode/…)`  
5. **验收：**  
   - 两次读同一 settings → 同 fp  
   - 写 `effective_settings.json` → 再读 → 同 fp  
   - 只改 `analysis.*` → settings_fp 不变  

非指纹字段：`meta` / `scanner` / `analysis` / `is_enabled` 等（`NON_FINGERPRINT_FIELDS`）。

---

## 6. 分批 TODO（小批次）

### Batch 0 — 规格冻结（本文）

- [x] 拍板 D1–D14、目录树、操作契约
- [x] 同步本文与实现（registry 平铺指纹、无 per-vid meta、无 fingerprint_index）

### Batch 1 — Artifact 布局与 VersionStore

**目标：** 新目录可 allocate / open / 写 registry；旧路径调用点改为新 API。

- [x] `ArtifactStore`：`simulations/{vid}/{enum|price|portfolio}/`
- [x] `simulations/meta.json`：`next_version_id` + `registry`；触顶拒绝 allocate
- [x] `{vid}/effective_settings.json`：`VersionMetaStore.write_effective_settings`
- [x] `ResultsRetention` / `prune_root`：按 **version 目录** keep-N
- [x] 单测：allocate、registry、prune、触顶拒绝
- [x] 停用 per-step 独立 `next_output_version`
- [x] 三步共享 vid（price/portfolio `allocate(version_id=enum)`）

### Batch 2 — 指纹与磁盘 cache hit

**目标：** 命中只认 `settings_fp + env_fp`；simulate 查磁盘 registry。

- [x] `FingerprintCalculator`：`settings_fp` = effective 子集 hash
- [x] DB `get_cache` 命中不再要求 `disk_settings_hash`
- [x] `SimulationVersionStore`：扫 registry 命中 step 产物
- [x] `Strategy.simulate`：优先磁盘 cache hit
- [x] miss：allocate → 写 registry + `effective_settings.json` → pipeline
- [x] 同 vid 补跑缺失 step
- [x] 指纹稳定性单测（§5）
- [x] **待做：** simulate 完全去掉 workbench DB fallback（Batch 3）

### Batch 3 — 退役工作台双轨缓存 / 「发布」

**目标：** CLI 与 UI 同一套 version 与 settings 文件。

- [x] `Strategy.simulate` / `_run_steps`：移除 `SimulationCacheManager` 读写
- [x] `EnumeratorPipeline.find_output_version_via_fps`：仅磁盘
- [x] `workbench_run`：simulate 结果读 step `version_id`（不再 `_workbench_version`）
- [x] BFF：`WorkbenchSnapshots` 读磁盘 `registry` + `effective_settings.json`
- [x] BFF apply settings：写 `settings.py` 后不再 touch DB 快照行
- [x] BFF：`WorkbenchCacheClear` / DELETE cache → 删磁盘 version
- [x] `WorkbenchSnapshots` / `result_report`：report hydrate 对齐 `{vid}/{step}/`
- [x] CLI `se/sp/so`：经 `Strategy.simulate` 单轨磁盘；输出 `version_id`
- [x] 文档：`BOUNDARY_NOTES` / `API.md` / BFF `strategy.md` 更新

### Batch 4 — 环境失效 / 强跑 / 恢复配置 UX

- [x] 打开 version：当前 env_fp vs registry → `env_invalid` 旗标
- [x] `env_invalid` 禁止 cache hit；CLI/BFF 提示「环境已失效」
- [x] 强制重跑（`ignore_cache` / `--force`）→ 不复用 enum，始终新 vid（D10）
- [x] 「恢复配置到 N」：读 `effective_settings.json`，round-trip 校验 `settings_fp` 后写 `settings.py`

### Batch 5 — 归因与 Report API 对齐

- [x] analyzer 读写 `{vid}/{step}/analysis/`（随 step `output_dir`）
- [x] demo 策略端到端：`simulate` + `sa` 验证新路径（`test_analysis_version_layout_e2e`）
- [x] BFF step report + `analysis.insights`（`Strategy.resolve_step_analysis`）
- [x] 更新 `engines/analyzer/TODO.md`

### Batch 6 — 清理与回归

- [x] 文档：旧 layout / legacy DB 清理（``VERSIONING_CLEANUP.md``）
- [x] 删除 ``SimulationCacheManager`` / ``sys_strategy_workbench_snapshot`` 表模型 / ``Strategy.clear_workbench_cache``
- [x] 回归单测：``test_versioning_regression.py`` + 既有 e2e 套件
- [ ] 用户盘 demo 旧 ``simulations/enum/N`` 目录（手动删后重跑，见清理文档）

**状态：** Batch 1–6 代码与文档已完成；用户盘 demo 产物需本地清理后验证。

---

## 7. 批次依赖

```text
Batch 0
  → Batch 1 ✅
      → Batch 2 ✅（DB fallback 待 Batch 3 收尾）
          → Batch 3 ✅（CLI + BFF 单轨磁盘）
          → Batch 4 / Batch 5 可部分并行
              → Batch 6
```

建议顺序：**3（CLI 单轨）→ 4 / 5 → 6**。

---

## 8. 每批完成定义（DoD）

- 有单测或脚本覆盖本批决策  
- 不引入「旧路径 fallback」  
- 更新本文对应 checkbox  
- 若改公开行为：更新 `API.md` / CLI help

---

## 9. 明确不做

- 旧 `simulations/enum/N` 自动迁移工具（默认可删重建）  
- 静默覆盖历史 version  
- `fingerprint_index` 反查表（registry 扫描即可）  
- `{vid}/meta.json`（索引与快照已分层：meta.json registry + effective_settings.json）  
- 三步合并为一次归因  

---

## 10. 相关代码锚点

| 区域 | 路径 |
|------|------|
| 产物布局 | `core/modules/strategy/core/services/artifacts/store.py` |
| registry / effective_settings | `.../artifacts/version_meta.py` |
| 磁盘 cache hit | `.../simulation_cache/version_store.py` |
| 指纹 | `.../simulation_cache/fingerprints.py` |
| 字段抽取规则 | `.../strategy_settings/strategy_settings.py`（`FINGERPRINT_FIELDS`） |
| simulate 编排 | `core/modules/strategy/core/strategy.py` |
| 清理说明 | `core/modules/strategy/docs/VERSIONING_CLEANUP.md` |
| 磁盘 cache 清理 | `.../workbench_cache/workbench_cache_clear.py` |
| 保留 | `.../results_retention/` |
| BFF 快照 | `core/bff/APIs/strategy/helpers/workbench_snapshots.py` |
| 归因 | `core/modules/strategy/core/engines/analyzer/` |
