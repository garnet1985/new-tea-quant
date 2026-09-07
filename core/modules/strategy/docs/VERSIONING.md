# Simulation versioning

**状态：** 现行规格（2026-09-03）  
**编号决策：** [notes/DECISIONS.md](./notes/DECISIONS.md)（D1–D39）  
**旧盘清理：** [notes/VERSIONING_CLEANUP.md](./notes/VERSIONING_CLEANUP.md)

一次完整回测 = 一个 version（enum / price / portfolio 共享该号）。日常编辑 SOT 是 `settings.py`；没有「发布策略」、没有工作台 DB 与磁盘双轨。

---

## 1. 用户动作（一张表）

| 动作 | 改 `settings.py`？ | 写哪个 `{vid}/`？ | 说明 |
|------|-------------------|-------------------|------|
| 打开 / 对比 version | 否 | 不写 | 只换报告。选中号 **不** 绑定 Run |
| 恢复配置 | 是（显式确认） | 不写产物 | 把 `{vid}/settings.json` 写回 `settings.py`；**不** 把 `scope.json` 的股票池写回运行时 |
| Run（非强制） | 工作台会先 Persist 草稿 | `(当前 execute_fp, 当前 env_fp)` 命中或新建 | 与选中号无关 |
| 强制重跑（`ignore_cache` / `--force`） | 同上 | **同一 vid**（命中键不变时） | 跳过 cache、不复用已有 enum 产物；复写上游则清下游。**不** 为同一双指纹再开号 |
| 固定 / 取消固定 | 否 | 不写 `{vid}/` | 只改 `meta.json` 根上的 `pinned` 列表 |
| 手动删除 | 否 | 删该 `{vid}/` | 已固定的也可删；并从 `pinned` 拿掉 |

主叙事：老 version 目录在当前环境下只读；Run 永远读当前 `settings.py` + 今天的股票池。要复现某号的配置，先恢复再跑。

---

## 2. 磁盘布局

```text
{strategy}/results/simulations/
  meta.json                         # 索引：next_version_id + registry + pinned
  {vid}/
    settings.json                   # 当时完整运行 settings（恢复用）
    effective_settings.json         # 白名单投影；不含 entity_ids
    scope.json                      # { entity_ids, start_date, end_date }
    enum/ | price/ | portfolio/
      runtime_env.json              # 该步完成标记
      analysis/                     # 与该步同生共死
```

`meta.json`：

```json
{
  "next_version_id": 4,
  "strategy_name": "demo/regression/rsi/rsi_v1_baseline",
  "last_updated": "...",
  "pinned": ["3", "6"],
  "registry": {
    "1": {
      "created_at": "...",
      "updated_at": "...",
      "execute_fp": "...",
      "env_fp": "...",
      "engine_version": "...",
      "steps": {"enumerate": "ok"}
    }
  }
}
```

约定：

- registry key 即 version id（`"3"`，不是 `"v3"`）。条目内不重复存 `version_id`。
- **`pinned` 只在根上**，不在 registry 行、不在 `{vid}/`。
- 指纹平铺为 `execute_fp` / `env_fp`；无 `fingerprint_index`，命中时线性扫 registry。
- `{vid}/` 身份归档三步共享、同身份只写一次（force / 补步不覆盖归档文件）。
- 步骤完成：registry `steps.{kind} = "ok"`；磁盘兜底 `{vid}/{step}/runtime_env.json`。

旧布局 `simulations/enum/N/` **不迁移**，见 [VERSIONING_CLEANUP.md](./notes/VERSIONING_CLEANUP.md)。

---

## 3. 两种指纹

划分标准：改 settings（或这次回测的 scope）能不能回到同一身份，不是「会不会影响结果」。

| | `execute_fp` | `env_fp` |
|--|--------------|----------|
| 含义 | 这次回测可逆的全部执行输入 | 用户改 settings/scope 回不去的环境 |
| 内容 | 白名单 settings ⊕ `scope.entity_ids`（排序后）。区间已在 `simulation` 内 | NTQ/core 版本、hooks 源码、DB 类型、data_contract 映射 |
| 白名单 | `strategy_settings/execute_fp_whitelist.py` → `StrategySettings.extract_execute_settings` | `FingerprintCalculator.to_env_fingerprint` |

不引入第三种 fp。`entity_ids` 只进 `execute_fp`，不要双边哈希。

胶囊「设置已变更」**只比** canonical effective（settings 投影 vs 当前选中 vid 的 freeze），**不比** 整个 `execute_fp`。股票池漂移会换号，但不是用户改了设置。

非 execute 字段（现有方向）：`meta` / `is_enabled` / `scanner` / `enumerator` / `analysis`。白名单 section 内的 UI 草稿 key 必须从投影剔除。

---

## 4. 何时换号

| 条件 | 行为 |
|------|------|
| 当前 `execute_fp` + 当前 `env_fp` 已有条目 | 命中该 vid（强制重跑则重算写入同一 vid，清下游） |
| settings 白名单变了 | `execute_fp` 变，新 vid |
| 只变 scope（解析出的股票池）settings 没改 | `execute_fp` 变，新 vid；胶囊不必报「设置已变更」 |
| env 变了，当前 env 下尚无该 `execute_fp` | 新 vid；旧 vid 留作档案 |
| env 变了，当前 env 下已有该 `execute_fp` | 命中新 env 那个 vid；旧 env vid 不动 |
| 只改非 effective 字段 | 不换号 |
| 只切换选中 version、未恢复、未跑 | 只换报告 |

被动变化（切步填默认、migrate、pprint、`1` vs `1.0`、空 `{}`）必须被 canonicalize 吃掉。

`env_invalid`：registry 存盘 `env_fp` ≠ 当前运行环境。该目录禁止 cache hit / 补步 / 写入；报告仍可打开、对比、恢复进 `settings.py`。Run 仍走当前 settings + 当前 env，**绝不写回**失效目录。UI：「环境已更新 / 仅供查阅」指产物只读，不是「不能跑」。

---

## 5. 固定（pin）与 keep-N

- 固定：列表置顶；自动清理与「即将清理」标记跳过 pinned。
- **不** 改 settings、**不** 绑定 Run、**不** 禁止手动删除。
- keep-N 上限：`data.json` → `retention.simulation_results_max_versions`（可被 `userspace/config/data.json` 覆盖）。触顶时 **allocate 拒绝**，不静默删。删未 pin 且号更靠前的。不因 `env_invalid` 加塞。
- CLI：`spn` / `sup` / `sdv`。BFF：`POST|DELETE …/version/:id/pin`，删除 `DELETE …/version/:id/cache`。

---

## 6. 恢复 vs 股票池

恢复只写 `settings.py`，不把历史 `scope.json.entity_ids` 设为当前运行股票池。下一次 Run 用今天的 `GlobalEntityCache.get_stock_list()` 算 `execute_fp`。池子若与当年不同，会开新号，不会覆盖旧报告。要「按当时那份配置跑」，恢复后再 Run 即可；要「按当时那批股票」，目前没有单独 Replay，池子漂移会自然开新 vid。

---

## 7. 代码锚点

| 区域 | 路径 |
|------|------|
| 指纹 | `core/services/fingerprint/fingerprint.py` |
| 白名单 | `engines/shared/services/strategy_settings/execute_fp_whitelist.py` |
| simulate / 强制重跑 | `core/strategy.py` → `Strategy.simulate` |
| registry / `{vid}/` / pin | `core/services/artifacts/version_meta.py` |
| cache hit | `core/services/artifacts/version_cache.py` |
| keep-N / 删除 | `core/services/artifacts/retention.py` |
| 工作台 Run | `core/bff/APIs/strategy/routes/runner/workbench_run.py` |
| 恢复 settings | `core/bff/APIs/strategy/routes/settings/apply.py` |
| 快照读模型 | `core/bff/APIs/strategy/helpers/workbench_snapshots.py` |
| HTTP | [BFF strategy.md](../../../bff/docs/routes/strategy.md) |
| 公开 API | [API.md](../API.md) |

---

## 8. 相关文档

| 文件 | 角色 |
|------|------|
| 本文 | **现行叙事 SOT** |
| [notes/DECISIONS.md](./notes/DECISIONS.md) | 编号决策日志（D1–D39） |
| [notes/VERSIONING_CLEANUP.md](./notes/VERSIONING_CLEANUP.md) | 旧 `enum/N` 布局与 legacy DB 一次性清理 |
| [notes/VERSIONING_REDESIGN.md](./notes/VERSIONING_REDESIGN.md) | 已归档过程稿 |
| [notes/SETTINGS_VERSION_IDENTITY.md](./notes/SETTINGS_VERSION_IDENTITY.md) | 已归档讨论纪要 |
