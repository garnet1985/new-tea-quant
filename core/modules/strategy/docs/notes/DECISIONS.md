# Settings / Version / Effective — 决策记录

更新时间：2026-09-02  
状态：已拍板（实施前以本文为准；与 [VERSIONING_REDESIGN.md](./VERSIONING_REDESIGN.md) D1–D14 冲突时，**以本文修订为准**）

讨论过程与否决项见 [SETTINGS_VERSION_IDENTITY.md](./SETTINGS_VERSION_IDENTITY.md)。

---

## 身份

| # | 决策 |
|---|------|
| D15 | **一次完整回测 = 一个 version。** 三步（enum / price / portfolio）共享该号。禁止「一步一个 version」或树状/DAG 版本。 |
| D16 | 指纹主键是 `(execute_fp, env_fp)`。`execute_fp` 哈希 **这次回测可逆的全部执行输入**（effective settings + scope 等），不是某一步的子集。 |
| D17 | 同 env + 同 effective：补跑缺失步、或复写任一已跑步 → **version 号不变**，写入同一 `{vid}/`。 |
| D18 | 同 version 上复写上游步：该 version 内 **下游产物删除（作废）**，步进器回到未跑；号不变。禁止留下会撒谎的旧下游报告。 |

D15 收紧 D3。D17 修正「已完成步骤一律 `force` → 新 vid」。  
**强制重新跑**：忽略已有产物、真正重算；命中键不变则 **仍写入同一 vid**（并按 D18 清下游）。禁止为同一 `(execute_fp, env_fp)` 再 allocate 一个号（否则下次非强制跑会不知道命中谁）。

---

## 切换版本 vs 运行（解耦）

| # | 决策 |
|---|------|
| D32 | **切换/恢复 version（用户确认后）会改 `settings.py`。** 这是显式恢复，不是静默。 |
| D33 | **运行与「当前选中哪个 version」无关。** 始终用当前 `settings.py` 算出的 `execute_fp` + **当前** `env_fp` 查找：命中则进缓存（除非强制重跑）。选中 v4 只决定看哪份报告，不决定写到哪。 |

因此「在 N 上继续跑」的路径是：确认恢复 N → settings 与 N 的 effective 对齐 → 再跑 → 若 env 也有效则命中 N。不是「选中 N 就绑定写入目标」。

---

## 配置怎么拆

| # | 决策 |
|---|------|
| D19 | **按功能块拆**（`core` / `data` / `goal` / `sampling` / `fees` / `simulation` / `portfolio` / `market_profile` …），**不按步骤拆**。 |
| D20 | 步骤只 **声明依赖哪些功能块**（清单写在引擎，用户不可改）。声明用于执行与校验，**不**把指纹粒度切到步骤。 |
| D21 | **现阶段保持单个 `settings.py`。** 按功能拆多文件是后续 UX，优先级低；仍禁止 `enum.yaml` / `price.yaml` / `portfolio.yaml`。 |

---

## Effective settings

| # | 决策 |
|---|------|
| D22 | **effective = 白名单抽取功能块 + canonicalize**（默认值、数值 coerce、去掉空占位 / UI 草稿 key）。 |
| D23 | 执行与指纹 **只使用** 这份 canonical effective。胶囊「设置已变更」也只比它，不比对原始 JSON 外形、不比对切步填的非 effective 字段。 |
| D24 | `settings → effective` 是投影（丢掉「其他」字段）。`effective → settings` 是把白名单字段 **merge 回** 完整 settings，「其他」保留。不是双射。 |
| D25 | `{vid}/` **必须归档当时完整 settings**（运行时 + 其他）。canonical effective 可另存作缓存；core/env 变了不得用新算法重算旧 effective 去命中。 |
| D26 | 不影响回测结果的字段进非 effective（现有方向：`meta` / `is_enabled` / `scanner` / `enumerator` / `analysis`）。白名单 section 内的 UI 草稿 key 必须从投影剔除。 |

D25 修订 D7：冻结不再只靠 `effective_settings.json` 子集。

---

## 两种指纹：`execute_fp` / `env_fp`

划分标准：**改 settings（或这次回测的 scope）能不能回到同一身份**，不是「会不会影响结果」。

| # | 决策 |
|---|------|
| D34 | **`execute_fp`**：`hash(FingerprintCalculator.extract_execute_payload(settings, entity_ids=...))`。白名单：`strategy_settings/execute_fp_whitelist.py`。抽取：`StrategySettings.extract_execute_settings`。settings = 白名单功能块；scope = 标的快照。区间已在 `simulation` 内。 |
| D35 | **`env_fp`**：用户改 settings/scope **回不去** 的执行环境。NTQ/core 版本、策略 hooks 源码、DB/合约映射等。 |
| D36 | **不引入第三种 fp。** scope 进 `execute_fp`，不要再塞进 `env_fp`。现实现把 `start_date` / `end_date` / `execution_mode` 编进 `env_fp`，必须拿出来。解析出的 `entity_ids` 是这次回测的标的快照，属 scope → `execute_fp`；**不要双边哈希**。胶囊「设置已变更」仍 **只比 settings 投影**，不比整个 `execute_fp`（股票池漂移不是用户改了设置）。 |

旧 version 的 `{vid}/` 只读，是因为 **不能把新环境的结果写进旧目录**。不是「正在看失效 version 时 Run 按钮报错」。Run 永远走 D33。恢复了一份新引擎已经不认的配置，失败发生在 **validate**，提示改 settings，而不是「版本只读所以不能跑」。

---

## 环境失效（`env_fp` 变化）

| # | 决策 |
|---|------|
| D27 | 旧 `{vid}/` **禁止 cache hit、禁止补步、禁止写入**。报告仍可打开、可对比、可恢复进 `settings.py`。 |
| D28 | **禁止**因 env 变化原地覆盖 `{vid}/` 产物。 |
| D29 | 运行始终 D33。查找 `(execute_fp, 当前 env_fp)`，命中或新建；**绝不写回**失效目录。 |
| D30 | UI：失效 version 标「环境已更新 / 仅供查阅」——指 **这份产物只读**。主展示按 settings 身份聚合。 |
| D31 | env 一变 **不批量删**。keep-N 满了：删 **未 pin 且 version 号更靠前（更旧）** 的；不因 `env_invalid` 加塞。UI 后期：快到期打「即将过期」。 |
| D37 | **当前 execute 身份在当前 env 下还没有 version：** 胶囊可挂最近一次同 settings 的旧号（如 v4）+「环境已更新」+「当前环境尚无结果」。主按钮「在当前环境回测」。0.x 可不做自动迁移。**大版本若旧报告格式也读不了，这套 UI 可能走不通，不阻塞当前实施。** |

---

## 何时换号（对照）

| 条件 | 行为 |
|------|------|
| 当前 execute_fp + 当前 env 已有 registry 条目 | 命中该 vid（强制重跑则重算并写入同一 vid，清下游） |
| settings 白名单变了 | execute_fp 变，新 vid |
| 只变 scope（如解析出的股票池）settings 没改 | execute_fp 变，新 vid；胶囊不必报「设置已变更」 |
| env 变了，当前 env 下尚无该 execute_fp | 新 vid；旧 vid 留作档案 |
| env 变了，当前 env 下已有该 execute_fp | 命中新 env 那个 vid；旧 env vid 不动 |
| 只改非 effective 字段 | execute_fp 不变，不换号 |
| 只切换选中的 version、未恢复、未跑 | 只换报告，不换号、不改 settings |

被动变化（切步填默认、migrate、pprint、`1` vs `1.0`、空 `{}`）必须被 canonicalize 吃掉，不得导致换号或胶囊误报。

---

## 明确否决

- 分步指纹 / 分步缓存作为用户可见 version（树状版本）
- 按回测步骤给用户各养一份 settings
- env 升级后原地覆盖旧报告以「维持同一 version 号」
- 用「是否点过控件」判断主动改设置；只认 canonical effective 是否变
- 因正在浏览 `env_invalid` version 就让 Run 直接报错（产物只读 ≠ 禁止在当前环境跑）
- 同一 `(execute_fp, env_fp)` 因强制重跑而新开第二个 vid
