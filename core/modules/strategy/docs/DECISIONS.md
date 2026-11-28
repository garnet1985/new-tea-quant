# Strategy — 设计与决策

**模块：** `modules.strategy` · **版本：** `0.12.3`

**最低支持核心版本：** `>=0.5.0`

本文记录本模块的设计目标、方案思路与拍板决策。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 设计目标

Strategy 主业：把用户策略钩子经 BacktestEngine `RunCallbacks` 挂进回测器，**不**另起平行调度或 session 框架。归因要回答「把止盈从 20% 改成 30%，结果变好了没有」这类问题——一次回测里旋钮是常数，单次回测本身回答不了。

约束与上下文：硬约束摘要如下，更长边界笔记见 [notes/BOUNDARY_NOTES.md](./notes/BOUNDARY_NOTES.md)；仿真 version / 指纹 / keep-N 见 [VERSIONING.md](./VERSIONING.md)；归因怎么运转见 [CONCEPTS.md](./CONCEPTS.md)；价格回放见 [notes/PRICE_REPLAY.md](./notes/PRICE_REPLAY.md)；选仓排序见 [notes/OPPORTUNITY_SELECTION.md](./notes/OPPORTUNITY_SELECTION.md)。

## 方案与思路

### 与 BacktestEngine（硬约束）

- **禁止** TimelineBuilder / 第二套 JobSession / Executor 空 proxy
- 时钟 → 切数据 → 业务：`Timeline.drive` → `on_tick` → `AsOfSlice` → 业务

### simulation_output 读路径

| 类型 | 职责 |
|------|------|
| `EnumOutput` | version 目录布局 |
| `EnumSource` | 下游只读句柄 |
| `investment_csv` | 投资/goal CSV 行模型 |

### Facade + contracts

- 包根仅 `Strategy`
- hooks / 枚举 / 共享数据类从 `contracts.py` 导入
- 公开 API 状态最高 `beta`（core 仍为 `0.x`）

### 设计点：归因不附在单次回测上（见 DEC-01）

**设计初衷**：一次回测里旋钮是常数，回答不了「把止盈从 20% 改成 30%，结果变好了没有」。

**设计背景**：平时 Run 要保持「把一个想法跑完」。若回测结束自动开多版本对照，每次改设置都会连带一整批价格和组合作废。

**解决方案**：

| 方案 | 做法摘要 | 优点 | 缺点 |
|------|----------|------|------|
| A：Run 顺便归因 | 一次 simulate 内解释旋钮 | 少一个入口 | 单次里旋钮不变，结论像在凑 |
| B：独立战役 | `sea` / `spa` / `soa` 另开；simulate 只回测 | 对照格按需补 | 须先有主 version |

### 设计点：一套副本，三个命令（见 DEC-02）

**设计初衷**：同一条「如果止损改成这样」要能在机会盘点、价格、组合上对到同一个 version。

**设计背景**：三层都算完很贵。用户改完止损后，后面两层会整批作废。

**解决方案**：

| 方案 | 做法摘要 | 优点 | 缺点 |
|------|----------|------|------|
| A：每层各养一套副本 | `sea` 只展机会盘点轴，`spa` 另展价格轴 | 每层配置看起来短 | 同一改动对不上号 |
| B：顶层 inputs 一套身份 | 命令只决定补到哪一层 | 三层读同一批号 | 配置不能按层拆开写 |

### 设计点：主答案是扫描曲线（见 DEC-03）

**设计初衷**：用户要的是「该把这个数字调成多少」，以及这一档附近稳不稳。

**设计背景**：几个回测格子拆不出唯一的「因子贡献了百分之几」。单笔 SHAP 解释的是入场现场和盈亏的相关，不是门槛该不该留。

**解决方案**：

| 方案 | 做法摘要 | 优点 | 缺点 |
|------|----------|------|------|
| A：有/无贡献度 + 敏感度两章 | 把每格差分归到旋钮上 | 看起来像分解 | 同时改多个轴就拆不开，也不是用户的主问题 |
| B：单因素多档曲线 + 排名 | 其余固定，只动一个轴；可选 `joint_sweep` 小矩阵 | 和调参方式一致 | 交互要额外声明 |

### 设计点：资金分配单独一轮（见 DEC-04）

**设计初衷**：槽位、分配方式、初始资金改的是买多少，不是想法。和止损、因子放进同一套副本，会为了资金再重跑机会盘点。

**设计背景**：只改 `portfolio.allocation` 时，机会盘点身份通常不变，可以复用已有机会盘点再补组合。

**解决方案**：

| 方案 | 做法摘要 | 优点 | 缺点 |
|------|----------|------|------|
| A：分配轴写进共用 inputs | 和因子一起展格 | 配置只有一处 | 资金档会乘进想法副本 |
| B：`allocation` 单独单因素 | 锚定当前主 version，复用机会盘点 | 想法战役和资金战役分开 | `soa` 多一轮格子 |

### 设计点：归因跟着策略 version（见 DEC-05）

**设计初衷**：策略从 version 1 变成 version 2 之后，不该还把 version 1 的对照报告当成当前结果。

**设计背景**：环境指纹只说明「还是这套代码和库」。主 version 变了，基准格已经不是上一场战役的那一格。

**解决方案**：

| 方案 | 做法摘要 | 优点 | 缺点 |
|------|----------|------|------|
| A：一组只按环境指纹 | 同环境的报告一直叠在当前按钮上 | 少一个键 | 换 version 后旧报告冒充当前 |
| B：环境指纹加主 version | 各组都留着；界面只显示当前主 version 那一组 | 回到旧 version 报告还在 | 同一环境可以有多组 |

---

## DEC-01：设计点：归因不附在单次回测上

- **采用：** B
- **理由：** 归因是事后对照，不是因子挖掘，也不改平时 Run 的含义。
- **影响：** 没有当前 settings 对应的主 version 时拒绝该层归因。

---

## DEC-02：设计点：一套副本，三个命令

- **采用：** B
- **理由：** 分层是为了懒执行，不是为了三套格子。
- **影响：** 轴只写顶层 `inputs`。写在层块里直接报错。

---

## DEC-03：设计点：主答案是扫描曲线

- **采用：** B
- **理由：** 默认匹配「一次改一个数」。联合扫描只在怀疑交互时加。
- **影响：** 贡献度章和单笔 SHAP 附录已不计算。全轴 `cross` 能展开，报告仍按单因素讲，口径未定。

---

## DEC-04：设计点：资金分配单独一轮

- **采用：** B
- **理由：** 组合层的主问题是钱有没有买到，不应把账户差再讲成一遍因子贡献。
- **影响：** 未写 `allocation` 时按当前 settings 出默认档。声明之后，单票上限、Kelly 系数、每笔手数不自动加扫。

---

## DEC-05：设计点：归因跟着策略 version

- **采用：** B
- **理由：** 对照的基准是当时的主 version，不是整个环境里所有号。
- **影响：** 不删除旧报告。`parent_version_id` 是组属于哪个策略 version；`baseline_version_id` 仍是对照用的基准格。

---

## DEC-06：D15: 一次完整回测 = 一个 version。

**一次完整回测 = 一个 version。** 三步（enum / price / portfolio）共享该号。禁止「一步一个 version」或树状/DAG 版本。

---

## DEC-07：D16: 指纹主键是 `(execute_fp, env_fp)`。`execute_fp` 哈希 **这次回

指纹主键是 `(execute_fp, env_fp)`。`execute_fp` 哈希 **这次回测可逆的全部执行输入**（effective settings + scope 等），不是某一步的子集。

---

## DEC-08：D17: 同 env + 同 effective：补跑缺失步、或复写任一已跑步 → **version 号不变

同 env + 同 effective：补跑缺失步、或复写任一已跑步 → **version 号不变**，写入同一 `{vid}/`。

---

## DEC-09：D18: 同 version 上复写上游步：该 version 内 **下游产物删除（作废）**，步进器回到未

同 version 上复写上游步：该 version 内 **下游产物删除（作废）**，步进器回到未跑；号不变。禁止留下会撒谎的旧下游报告。

---

## DEC-10：D32: 切换/恢复 version（用户确认后）会改 `settings.py`。

**切换/恢复 version（用户确认后）会改 `settings.py`。** 这是显式恢复，不是静默。

---

## DEC-11：D33: 运行与「当前选中哪个 version」无关。

**运行与「当前选中哪个 version」无关。** 始终用当前 `settings.py` 算出的 `execute_fp` + **当前** `env_fp` 查找：命中则进缓存（除非强制重跑）。选中 v4 只决定看哪份报告，不决定写到哪。

---

## DEC-12：D19: 按功能块拆

**按功能块拆**（`core` / `data` / `goal` / `sampling` / `fees` / `simulation` / `portfolio` / `market_profile` …），**不按步骤拆**。

---

## DEC-13：D20: 步骤只 **声明依赖哪些功能块**（清单写在引擎，用户不可改）。声明用于执行与校验，**不**把指纹

步骤只 **声明依赖哪些功能块**（清单写在引擎，用户不可改）。声明用于执行与校验，**不**把指纹粒度切到步骤。

---

## DEC-14：D21: 现阶段保持单个 `settings.py`。

**现阶段保持单个 `settings.py`。** 按功能拆多文件是后续 UX，优先级低；仍禁止 `enum.yaml` / `price.yaml` / `portfolio.yaml`。

---

## DEC-15：D22: effective = 白名单抽取功能块 + canonicalize

**effective = 白名单抽取功能块 + canonicalize**（默认值、数值 coerce、去掉空占位 / UI 草稿 key）。

---

## DEC-16：D23: 执行与指纹 **只使用** 这份 canonical effective。胶囊「设置已变更」也只比它

执行与指纹 **只使用** 这份 canonical effective。胶囊「设置已变更」也只比它，不比对原始 JSON 外形、不比对切步填的非 effective 字段。

---

## DEC-17：D24: `settings → effective` 是投影（丢掉「其他」字段）。`effective → 

`settings → effective` 是投影（丢掉「其他」字段）。`effective → settings` 是把白名单字段 **merge 回** 完整 settings，「其他」保留。不是双射。

---

## DEC-18：D25: `{vid}/` **必须归档当时完整 settings**（运行时 + 其他）。canonical

`{vid}/` **必须归档当时完整 settings**（运行时 + 其他）。canonical effective 可另存作缓存；core/env 变了不得用新算法重算旧 effective 去命中。

---

## DEC-19：D26: 不影响回测结果的字段进非 effective（现有方向：`meta` / `is_enabled` 

不影响回测结果的字段进非 effective（现有方向：`meta` / `is_enabled` / `scanner` / `enumerator`）。白名单 section 内的 UI 草稿 key 必须从投影剔除。`analysis` 已退役，残留块不进指纹。

---

## DEC-20：D34: `execute_fp`

**`execute_fp`**：`hash(FingerprintCalculator.extract_execute_payload(settings, entity_ids=...))`。白名单：`strategy_settings/execute_fp_whitelist.py`。抽取：`StrategySettings.extract_execute_settings`。settings = 白名单功能块；scope = 标的快照。区间已在 `simulation` 内。

---

## DEC-21：D35: `env_fp`

**`env_fp`**：用户改 settings/scope **回不去** 的执行环境。NTQ/core 版本、策略 hooks 源码、DB/合约映射等。

---

## DEC-22：D36: 不引入第三种 fp。

**不引入第三种 fp。** scope 进 `execute_fp`，不要再塞进 `env_fp`。解析出的 `entity_ids` 是这次回测的标的快照，属 scope → `execute_fp`；**不要双边哈希**。胶囊「设置已变更」仍 **只比 settings 投影**，不比整个 `execute_fp`。

---

## DEC-23：D27: 旧 `{vid}/` **禁止 cache hit、禁止补步、禁止写入**。报告仍可打开、可对比、可

旧 `{vid}/` **禁止 cache hit、禁止补步、禁止写入**。报告仍可打开、可对比、可恢复进 `settings.py`。

---

## DEC-24：D28: 禁止

**禁止**因 env 变化原地覆盖 `{vid}/` 产物。

---

## DEC-25：D29: 运行始终 D33。查找 `(execute_fp, 当前 env_fp)`，命中或新建；**绝不写回

运行始终 D33。查找 `(execute_fp, 当前 env_fp)`，命中或新建；**绝不写回**失效目录。

---

## DEC-26：D30: UI：失效 version 标「环境已更新 / 仅供查阅」——指 **这份产物只读**。

UI：失效 version 标「环境已更新 / 仅供查阅」——指 **这份产物只读**。

---

## DEC-27：D31: 已由 D40 取代。

**已由 D40 取代。** 旧口径：env 一变不批量删；keep-N 按未 pin 的旧 version 号切。

---

## DEC-28：D37: 当前 execute 身份在当前 env 下还没有 version：

**当前 execute 身份在当前 env 下还没有 version：** 胶囊可挂最近一次同 settings 的旧号 +「环境已更新」+「当前环境尚无结果」。主按钮「在当前环境回测」。0.x 不做自动迁移。

---

## DEC-29：D40: 清理主键是 `env_fp`。

**清理主键是 `env_fp`。** 当前环境整组保留。过时环境最多留 N 组（`retention.simulation_results_max_stale_envs`），超出删最旧一组（simulation 号 + 对应归因组）。没有 pin。环境变了不立刻物理删除。

---

## DEC-30：D38: 工作台占用：

**工作台占用：** 前端长期只持有草稿。胶囊「设置已变更」= 草稿 execute 投影 vs **当前选中 vid 的 freeze**（`effective_settings`）。「文件已更新」= 草稿 vs 当前 `settings.py`，rev 为文件字节 sha256。进页 / 设置区 focus / Run·Persist / 恢复前探测磁盘；草稿干净且 rev 变了则静默灌盘，草稿脏且 rev 变了则冲突框。Persist/Run/恢复带 If-Match；写盘后回读新 rev。

---

## DEC-31：D39: 已由 D40 取消。

**已由 D40 取消。** 旧口径：`meta.pinned` 挡 keep-N。清理改按环境整组后不再需要 pin。

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
