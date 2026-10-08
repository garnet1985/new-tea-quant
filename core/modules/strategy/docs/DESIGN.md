# Strategy — 设计说明

**模块：** `modules.strategy` · **版本：** `0.10.0`

硬约束摘要如下；更长边界笔记见 [notes/BOUNDARY_NOTES.md](./notes/BOUNDARY_NOTES.md)。

仿真 version / 指纹 / keep-N 见 [VERSIONING.md](./VERSIONING.md)。编号决策在文末。  
归因怎么运转见 [CONCEPTS.md](./CONCEPTS.md)；结构见 [ARCHITECTURE.md](./ARCHITECTURE.md)。价格回放见 [notes/PRICE_REPLAY.md](./notes/PRICE_REPLAY.md)。选仓排序见 [notes/OPPORTUNITY_SELECTION.md](./notes/OPPORTUNITY_SELECTION.md)。

---

## 与 BacktestEngine（硬约束）

Strategy 主业：把用户策略钩子经 BE `RunCallbacks` 挂进回测器。**不**另起平行调度或 session 框架。

- **禁止** TimelineBuilder / 第二套 JobSession / Executor 空 proxy
- 时钟 → 切数据 → 业务：`Timeline.drive` → `on_tick` → `AsOfSlice` → 业务

---

## simulation_output 读路径

| 类型 | 职责 |
|------|------|
| `EnumOutput` | version 目录布局 |
| `EnumSource` | 下游只读句柄 |
| `investment_csv` | 投资/goal CSV 行模型 |

---

## Facade + contracts

- 包根仅 `Strategy`
- hooks / 枚举 / 共享数据类从 `contracts.py` 导入
- 公开 API 状态最高 `beta`（core 仍为 `0.x`）

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [API.md](../API.md)
- [VERSIONING.md](./VERSIONING.md)
- [BOUNDARY_NOTES.md](./notes/BOUNDARY_NOTES.md)
- [CONCEPTS.md](./CONCEPTS.md)
- [PRICE_REPLAY.md](./notes/PRICE_REPLAY.md)
- [OPPORTUNITY_SELECTION.md](./notes/OPPORTUNITY_SELECTION.md)

---

## 设计点：归因不附在单次回测上

### 设计初衷

一次回测里旋钮是常数，回答不了「把止盈从 20% 改成 30%，结果变好了没有」。

### 设计背景

平时 Run 要保持「把一个想法跑完」。若回测结束自动开多版本对照，每次改设置都会连带一整批价格和组合作废。

### 解决方案

| 方案 | 做法摘要 | 优点 | 缺点 |
|------|----------|------|------|
| A：Run 顺便归因 | 一次 simulate 内解释旋钮 | 少一个入口 | 单次里旋钮不变，结论像在凑 |
| B：独立战役 | `sea` / `spa` / `soa` 另开；simulate 只回测 | 对照格按需补 | 须先有主 version |

### 决定

- **采用：** B
- **理由：** 归因是事后对照，不是因子挖掘，也不改平时 Run 的含义。
- **影响：** 没有当前 settings 对应的主 version 时拒绝该层归因。

---

## 设计点：一套副本，三个命令

### 设计初衷

同一条「如果止损改成这样」要能在枚举、价格、组合上对到同一个 version。

### 设计背景

三层都算完很贵。用户改完止损后，后面两层会整批作废。

### 解决方案

| 方案 | 做法摘要 | 优点 | 缺点 |
|------|----------|------|------|
| A：每层各养一套副本 | `sea` 只展枚举轴，`spa` 另展价格轴 | 每层配置看起来短 | 同一改动对不上号 |
| B：顶层 inputs 一套身份 | 命令只决定补到哪一层 | 三层读同一批号 | 配置不能按层拆开写 |

### 决定

- **采用：** B
- **理由：** 分层是为了懒执行，不是为了三套格子。
- **影响：** 轴只写顶层 `inputs`。写在层块里直接报错。

---

## 设计点：主答案是扫描曲线

### 设计初衷

用户要的是「该把这个数字调成多少」，以及这一档附近稳不稳。

### 设计背景

几个回测格子拆不出唯一的「因子贡献了百分之几」。单笔 SHAP 解释的是入场现场和盈亏的相关，不是门槛该不该留。

### 解决方案

| 方案 | 做法摘要 | 优点 | 缺点 |
|------|----------|------|------|
| A：有/无贡献度 + 敏感度两章 | 把每格差分归到旋钮上 | 看起来像分解 | 同时改多个轴就拆不开，也不是用户的主问题 |
| B：单因素多档曲线 + 排名 | 其余固定，只动一个轴；可选 `joint_sweep` 小矩阵 | 和调参方式一致 | 交互要额外声明 |

### 决定

- **采用：** B
- **理由：** 默认匹配「一次改一个数」。联合扫描只在怀疑交互时加。
- **影响：** 贡献度章和单笔 SHAP 附录已不计算。全轴 `cross` 能展开，报告仍按单因素讲，口径未定。

---

## 设计点：资金分配单独一轮

### 设计初衷

槽位、分配方式、初始资金改的是买多少，不是想法。和止损、因子放进同一套副本，会为了资金再重跑枚举。

### 设计背景

只改 `portfolio.allocation` 时，枚举身份通常不变，可以复用已有枚举再补组合。

### 解决方案

| 方案 | 做法摘要 | 优点 | 缺点 |
|------|----------|------|------|
| A：分配轴写进共用 inputs | 和因子一起展格 | 配置只有一处 | 资金档会乘进想法副本 |
| B：`allocation` 单独单因素 | 锚定当前主 version，复用枚举 | 想法战役和资金战役分开 | `soa` 多一轮格子 |

### 决定

- **采用：** B
- **理由：** 组合层的主问题是钱有没有买到，不应把账户差再讲成一遍因子贡献。
- **影响：** 未写 `allocation` 时按当前 settings 出默认档。声明之后，单票上限、Kelly 系数、每笔手数不自动加扫。

---

## 设计点：归因跟着策略 version

### 设计初衷

策略从 version 1 变成 version 2 之后，不该还把 version 1 的对照报告当成当前结果。

### 设计背景

环境指纹只说明「还是这套代码和库」。主 version 变了，基准格已经不是上一场战役的那一格。

### 解决方案

| 方案 | 做法摘要 | 优点 | 缺点 |
|------|----------|------|------|
| A：一组只按环境指纹 | 同环境的报告一直叠在当前按钮上 | 少一个键 | 换 version 后旧报告冒充当前 |
| B：环境指纹加主 version | 各组都留着；界面只显示当前主 version 那一组 | 回到旧 version 报告还在 | 同一环境可以有多组 |

### 决定

- **采用：** B
- **理由：** 对照的基准是当时的主 version，不是整个环境里所有号。
- **影响：** 不删除旧报告。`parent_version_id` 是组属于哪个策略 version；`baseline_version_id` 仍是对照用的基准格。

---

## 编号决策（原 DECISIONS.md）

更新时间：2026-09-03。布局与运行时契约已写入 [VERSIONING.md](./VERSIONING.md)，这里只留编号。

### 身份

| # | 决策 |
|---|------|
| D15 | **一次完整回测 = 一个 version。** 三步（enum / price / portfolio）共享该号。禁止「一步一个 version」或树状/DAG 版本。 |
| D16 | 指纹主键是 `(execute_fp, env_fp)`。`execute_fp` 哈希 **这次回测可逆的全部执行输入**（effective settings + scope 等），不是某一步的子集。 |
| D17 | 同 env + 同 effective：补跑缺失步、或复写任一已跑步 → **version 号不变**，写入同一 `{vid}/`。 |
| D18 | 同 version 上复写上游步：该 version 内 **下游产物删除（作废）**，步进器回到未跑；号不变。禁止留下会撒谎的旧下游报告。 |

D15 收紧早期「一步一个 version」。D17 修正「已完成步骤一律 `force` → 新 vid」。  
**强制重新跑**：忽略已有产物、真正重算；命中键不变则 **仍写入同一 vid**（并按 D18 清下游）。禁止为同一 `(execute_fp, env_fp)` 再 allocate 一个号。

### 切换版本 vs 运行

| # | 决策 |
|---|------|
| D32 | **切换/恢复 version（用户确认后）会改 `settings.py`。** 这是显式恢复，不是静默。 |
| D33 | **运行与「当前选中哪个 version」无关。** 始终用当前 `settings.py` 算出的 `execute_fp` + **当前** `env_fp` 查找：命中则进缓存（除非强制重跑）。选中 v4 只决定看哪份报告，不决定写到哪。 |

因此「在 N 上继续跑」的路径是：确认恢复 N → settings 与 N 的 effective 对齐 → 再跑 → 若 env 也有效则命中 N。

### 配置怎么拆

| # | 决策 |
|---|------|
| D19 | **按功能块拆**（`core` / `data` / `goal` / `sampling` / `fees` / `simulation` / `portfolio` / `market_profile` …），**不按步骤拆**。 |
| D20 | 步骤只 **声明依赖哪些功能块**（清单写在引擎，用户不可改）。声明用于执行与校验，**不**把指纹粒度切到步骤。 |
| D21 | **现阶段保持单个 `settings.py`。** 按功能拆多文件是后续 UX，优先级低；仍禁止 `enum.yaml` / `price.yaml` / `portfolio.yaml`。 |

### Effective settings

| # | 决策 |
|---|------|
| D22 | **effective = 白名单抽取功能块 + canonicalize**（默认值、数值 coerce、去掉空占位 / UI 草稿 key）。 |
| D23 | 执行与指纹 **只使用** 这份 canonical effective。胶囊「设置已变更」也只比它，不比对原始 JSON 外形、不比对切步填的非 effective 字段。 |
| D24 | `settings → effective` 是投影（丢掉「其他」字段）。`effective → settings` 是把白名单字段 **merge 回** 完整 settings，「其他」保留。不是双射。 |
| D25 | `{vid}/` **必须归档当时完整 settings**（运行时 + 其他）。canonical effective 可另存作缓存；core/env 变了不得用新算法重算旧 effective 去命中。 |
| D26 | 不影响回测结果的字段进非 effective（现有方向：`meta` / `is_enabled` / `scanner` / `enumerator`）。白名单 section 内的 UI 草稿 key 必须从投影剔除。`analysis` 已退役，残留块不进指纹。 |

### 两种指纹

划分标准：**改 settings（或这次回测的 scope）能不能回到同一身份**，不是「会不会影响结果」。

| # | 决策 |
|---|------|
| D34 | **`execute_fp`**：`hash(FingerprintCalculator.extract_execute_payload(settings, entity_ids=...))`。白名单：`strategy_settings/execute_fp_whitelist.py`。抽取：`StrategySettings.extract_execute_settings`。settings = 白名单功能块；scope = 标的快照。区间已在 `simulation` 内。 |
| D35 | **`env_fp`**：用户改 settings/scope **回不去** 的执行环境。NTQ/core 版本、策略 hooks 源码、DB/合约映射等。 |
| D36 | **不引入第三种 fp。** scope 进 `execute_fp`，不要再塞进 `env_fp`。解析出的 `entity_ids` 是这次回测的标的快照，属 scope → `execute_fp`；**不要双边哈希**。胶囊「设置已变更」仍 **只比 settings 投影**，不比整个 `execute_fp`。 |

旧 version 的 `{vid}/` 只读，是因为 **不能把新环境的结果写进旧目录**。不是「正在看失效 version 时 Run 按钮报错」。恢复了一份新引擎已经不认的配置，失败发生在 **validate**。

### 环境失效

| # | 决策 |
|---|------|
| D27 | 旧 `{vid}/` **禁止 cache hit、禁止补步、禁止写入**。报告仍可打开、可对比、可恢复进 `settings.py`。 |
| D28 | **禁止**因 env 变化原地覆盖 `{vid}/` 产物。 |
| D29 | 运行始终 D33。查找 `(execute_fp, 当前 env_fp)`，命中或新建；**绝不写回**失效目录。 |
| D30 | UI：失效 version 标「环境已更新 / 仅供查阅」——指 **这份产物只读**。 |
| D31 | **已由 D40 取代。** 旧口径：env 一变不批量删；keep-N 按未 pin 的旧 version 号切。 |
| D37 | **当前 execute 身份在当前 env 下还没有 version：** 胶囊可挂最近一次同 settings 的旧号 +「环境已更新」+「当前环境尚无结果」。主按钮「在当前环境回测」。0.x 不做自动迁移。 |
| D40 | **清理主键是 `env_fp`。** 当前环境整组保留。过时环境最多留 N 组（`retention.simulation_results_max_stale_envs`），超出删最旧一组（simulation 号 + 对应归因组）。没有 pin。环境变了不立刻物理删除。 |

### 工作台占用

| # | 决策 |
|---|------|
| D38 | **工作台占用：** 前端长期只持有草稿。胶囊「设置已变更」= 草稿 execute 投影 vs **当前选中 vid 的 freeze**（`effective_settings`）。「文件已更新」= 草稿 vs 当前 `settings.py`，rev 为文件字节 sha256。进页 / 设置区 focus / Run·Persist / 恢复前探测磁盘；草稿干净且 rev 变了则静默灌盘，草稿脏且 rev 变了则冲突框。Persist/Run/恢复带 If-Match；写盘后回读新 rev。 |

### 固定（pin）

| # | 决策 |
|---|------|
| D39 | **已由 D40 取消。** 旧口径：`meta.pinned` 挡 keep-N。清理改按环境整组后不再需要 pin。 |

### 何时换号

| 条件 | 行为 |
|------|------|
| 当前 execute_fp + 当前 env 已有 registry 条目 | 命中该 vid（强制重跑则重算并写入同一 vid，清下游） |
| settings 白名单变了 | execute_fp 变，新 vid |
| 只变 scope（如解析出的股票池）settings 没改 | execute_fp 变，新 vid；胶囊不必报「设置已变更」 |
| env 变了，当前 env 下尚无该 execute_fp | 新 vid；旧 vid 留作档案 |
| env 变了，当前 env 下已有该 execute_fp | 命中新 env 那个 vid；旧 env vid 不动 |
| 只改非 effective 字段 | execute_fp 不变，不换号 |
| 只切换选中的 version、未恢复、未跑 | 只换报告，不换号、不改 settings |

被动变化（切步填默认、pprint、`1` vs `1.0`、空 `{}`）必须被 canonicalize 吃掉，不得导致换号或胶囊误报。

### 明确否决

- 分步指纹 / 分步缓存作为用户可见 version（树状版本）
- 按回测步骤给用户各养一份 settings
- env 升级后原地覆盖旧报告以「维持同一 version 号」
- 用「是否点过控件」判断主动改设置；只认 canonical effective 是否变
- 因正在浏览 `env_invalid` version 就让 Run 直接报错（产物只读 ≠ 禁止在当前环境跑）
- 同一 `(execute_fp, env_fp)` 因强制重跑而新开第二个 vid
- 用 pin 挡自动清理，或按 version 号从当前环境里抽走几格
- 恢复配置时把 `scope.json` 的股票池写回运行时（恢复只写 `settings.py`）
- 独立 Replay 动作（要复现历史配置：先恢复再 Run）
