# Strategy — 设计说明

**模块：** `modules.strategy` · **版本：** `0.10.0`

硬约束摘要如下；更长边界笔记见 [notes/BOUNDARY_NOTES.md](./notes/BOUNDARY_NOTES.md)。

仿真 version / 指纹 / 固定 / keep-N 见 [VERSIONING.md](./VERSIONING.md)。  
编号决策：[notes/DECISIONS.md](./notes/DECISIONS.md)。  
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

## 自由函数现状

- 模块内约 29 个无下划线顶层 `def`，**绝大多数仅模块内使用**（helpers / package / timeline 等）。
- **跨模块入口**此前主要是 `package_cli.run_export` / `run_strategy_bundle_import`（CLI）；已收为 **`PackageCli`** 类方法。
- BFF / tag / adapter 的 deep-import 多为**类**（`DiscoveryService`、`ReportManager` 等），不在「自由函数类化」范围内；全量改走 Facade 另开专项。

---

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [API.md](../API.md)
- [VERSIONING.md](./VERSIONING.md)
- [BOUNDARY_NOTES.md](./notes/BOUNDARY_NOTES.md)
- [DECISIONS.md](./notes/DECISIONS.md)
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
