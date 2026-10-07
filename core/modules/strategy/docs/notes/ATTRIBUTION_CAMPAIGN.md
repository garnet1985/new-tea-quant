# 矩阵归因（战役）

**状态：** 口径修订（2026-10-03）。回测与归因拆开。核心概念见下文 §0；**产品目标**见 [ATTRIBUTION_SWEEP.md](./ATTRIBUTION_SWEEP.md)；配置细节 [ATTRIBUTION_INPUTS.md](./ATTRIBUTION_INPUTS.md)。  
**一句话：** 先展开一套共用扫描点（「如果」副本），再按层懒补产物，用该层指标做单因素曲线 / 敏感度排序（可选联合扫）。  
**位置：** 业务在 `strategy/engines/analyzer`（`pipeline.py` 只串步骤；实施在 `steps/campaign/`）。统计原语仍在 `modules.analysis`。  
**问什么：** [ATTRIBUTION.md](./ATTRIBUTION.md) / [ATTRIBUTION_SWEEP.md](./ATTRIBUTION_SWEEP.md)；展示 [ATTRIBUTION_PRESENT.md](./ATTRIBUTION_PRESENT.md)；枚举 [ATTRIBUTION_ENUM.md](./ATTRIBUTION_ENUM.md)；价格 [ATTRIBUTION_PRICE.md](./ATTRIBUTION_PRICE.md) / [PRICE_REPLAY.md](./PRICE_REPLAY.md)；组合 [ATTRIBUTION_PORTFOLIO.md](./ATTRIBUTION_PORTFOLIO.md)。

---

## 0. 锁定概念（先于配置细节）

### 0.1 「如果」副本：一套身份，三层共用

参数归因的本质是：相对当前想法（主 version / 基准格），用若干 **副本** 回答「如果旋钮改成这样，结局怎样」。

- 副本由 `attribution.py` 里声明的 settings 路径取值展开而来，号为 `{vid}-{r}`，不占用主号序列。
- **所有归因层共用同一套副本身份。** 不是枚举一套、价格一套、组合再一套。
- 某副本改了止损或因子：枚举 / 价格 / 组合若已跑齐，三层都应能在**同一 version 号**上读到各自产物，再和原版比。
- 只改组合槽位时：枚举 / 价格指纹可能与基准相同 → **复用**已有上下游产物即可，不必为了「有结果」去改想法参数；组合层仍有自己的差异可归因。

**错误模型（已否定）：** `sea` / `spa` / `soa` 各自只展本层 `inputs`、各自养各的副本集合。

### 0.2 为什么还要三个命令

分层**不是**为了三套副本，而是为了 **算力上的懒执行**：

| CLI | 补全到哪一层产物 | 典型场景 |
|-----|------------------|----------|
| `sea` | 每个共用副本 **只跑枚举** | 调止损 / 因子；后两层尚未定稿，不算价格与组合 |
| `spa` | 同一批副本 **再补价格**（依赖已有枚举） | 枚举满意后，看去噪等权账 |
| `soa` | 同一批副本 **再补组合**（依赖已有价格） | 再看资金是否买到该买的 |

矩阵归因比单次回测贵得多。若 `sea` 就把三层算完，用户改完止损后价格 / 组合结果整批作废，是浪费。  
主 version 仍须先有对应层平时产物（`se` / `sp` / `so`）；缺主号则拒绝该层归因。

### 0.3 共用管道（每层 CLI 各跑一遍）

`sea` / `spa` / `soa` **共享同一种 pipeline 形状**，不是三套不同编排。每一层入口都走：

```text
解析「如果」取值（共用展格 → 副本身份）
  → 补全本层产物（plan task → execute task；只 simulate 到本层）
  → 收集产物（gather）
  → 对照 / 总结（attribute → summarize）
  → 报告 / 落盘（report → persist）
```

差别只有：

1. **execute 补到哪一层**（枚举 / 价格 / 组合）；
2. **gather / summarize / report 读哪一套因变量**（见 INPUTS §2）。

归因前第一件事是把该层需要的副本产物跑齐，再抓数总结——不是先总结再补洞。

### 0.4 与配置的关系

- **自变量（展格）** 决定「有哪些如果」→ 共用副本身份。写法见 [ATTRIBUTION_INPUTS.md](./ATTRIBUTION_INPUTS.md)。
- **因变量（解读）** 仍按层固定；用户不配置「要解释什么」。
- 配置形态若仍按 `enumerate` / `price_factor` / `portfolio` 分块存放轴，**展格时必须合并为同一套身份**；禁止「跑哪层 CLI 就只展哪层块」。目标形态是一份战役共用 `inputs`（细节以 INPUTS 为准）。

### 0.5 产品形态：参数扫描（见 SWEEP）

- **默认：** 单因素多档扫描 → 每层报告输出敏感度排名 + 每轴曲线（该层纵轴）。  
- **可选：** `joint_sweep` 指定轴子集小矩阵；不是默认全轴 `cross`。  
- **报告按层选题呈现**（枚举强调机会轴，组合强调资金轴）；**不是**每层私有展格。  
- 差距与实施顺序：[ATTRIBUTION_SWEEP.md](./ATTRIBUTION_SWEEP.md) §7–8。

---

## 1. 为什么去掉单次归因

一次 Run 里 settings 旋钮是常数。对「把止盈从 20% 改成 30%，账户变好了没有」这个问题，单次回测内部的共变回答不了，报告看起来会像在玩。

因此：

- `Strategy.simulate` 只回测，不写归因
- 取消 CLI `sa` / `sz`；归因入口按层拆成 `sea` / `spa` / `soa`（**懒补产物**，见 §0.2）
- 无当前 settings 对应主 version 时拒绝归因（提示先 `se` / `sp` / `so`）
- 对照格写入副本 `{vid}-{r}`，不占用主号序列
- 单 version 的 prepare / analyze / report / layer 已删除；单笔 SHAP 附录已删除。

---

## 2. 默认 Run 是什么

默认跑策略 = 验证这一次的想法：一个 `settings.py`、一个主 version。不自动开多版本战役，也不在回测后自动归因。
专门要对照旋钮时再开独立入口。它先读已经留下的号；只有用户明确要补格子、而且现有号盖不住时，才额外调用 `Strategy.simulate`。那是这一次战役自己的事，不改变平时 Run 的含义。

strategy 仍然是「把一个想法跑完」。归因是事后对照，不是因子挖掘器。全市场因子研究（IC / 滚动 / 离开某一条策略）留给以后的 `factor` 产品线。

---

## 3. Group ≠ 可以归因

这两个词不要混用。

**Group（归档）**  
键是 `env_fp`。代码、NTQ 版本、库类型、data contract 没变，跑过的 version 都记进去。一年、三年、滚动窗里的每一段，只要环境没变，都进这一组。组是「这部策略在这个环境下跑过哪些号」，不是「可以倒进同一张回归表」。

`group_meta` 里再按样本窗做一层索引：区间 + 股票池 → 这批 version。

同一对 `(execute_fp, env_fp)` 命中旧号时不要重复记。

**可以归因（某一次任务的样本）**  
参数战役只收与这次快照 **区间、股票池相同** 的号，真正不同的只有**共用展格**声明路径上的取值（见 §0.1）。`core` 字段改名、钩子源码改了 → `env_fp` 变 → 新 group，旧命名空间停在旧组。

同组只说明「还是那套策略环境」。进不进这一张表，看这次任务锁的是哪一种样本。

不要把日期塞进 `env_fp`。区间改得回去，不属于环境。也不要为归因再加第三种指纹；两枚已经够圈出「同环境、同一样本、只改旋钮」。

---

## 4. 三种任务（后两种可后做）

| 任务 | 锁什么 | 动什么 | 不要做的 |
|------|--------|--------|----------|
| **参数归因（inputs）** | 这次快照的区间和股票池 | 战役共用 `inputs` 声明的 settings 路径 | 把一年和三年当成同一轴的两个取值；按 CLI 各养各的副本 |
| **滚动验证** | 旋钮（或很少几组完整设置） | 声明好的窗口 | 和参数战役混在一份报告里 |
| **单次内部切片** | 这一版已留下的 snapshot | 现场 RSI 等与单笔盈亏 | 每次回测默认跑；不要叫成战役 |

产物可以仍写在同一个 `results/attribution/{group}/` 下，**任务类型分开**。

决策模拟不进自动扫描：那一层改的是人选谁、买多少，不是设置旋钮。

---

## 5. 流程

平时 Run 只多写一行组成员（落地时），不额外跑回测。

归因是单独入口。点名方式见 [§10](#10-attributionpy) 与 [ATTRIBUTION_INPUTS.md](./ATTRIBUTION_INPUTS.md)。用当前 `settings.py` 的 effective 当快照；**共用展格**时自动加当前 settings 为基准格；`cross: false`（默认）每次只改一个路径；`cross: true` 做笛卡尔积。

```text
读当前 settings 快照 + attribution.py
  → 解析顶层 inputs（未声明时用共用默认轴）→ oaat 展格
  → 全轴 cross 仍可展开，报告口径未定
  → 同一身份只分配一个副本号；execute 只补「当前 CLI 层」产物（上游缺则先补上游）
  → gather / 归因 / 总结；报告只含该层固定结果指标
  → 命中 / 补跑由回测层按双指纹判断
```

配置是策略旁的 `attribution.py`，不是 `settings.analysis` 开关，不进指纹。

磁盘：

```text
{strategy}/results/attribution/
  meta.json              # next_group_id；env_fp → 1、2、3…
    {n}/                   # 组号，不是指纹
    group_meta.json      # 含 env_fp；宜记录本战役共用副本身份列表
    enumerate/ | price_factor/ | portfolio/   # 按 CLI 层分目录（报告与总结，不是三套格子）
      report.json
      table.json
      attribute.json
      task_meta.json
    rolling/             # 滚动验证（读 attribution.rolling）
```

一次 CLI 只**总结**一层指标，但对照的 version 集合是共用的那一套：

- `sea`：机会够不够、密不密、门与目标路径
- `spa`：去噪后等权机会账；可附 Trades/XGB
- `soa`：资金折损、买到 vs 漏掉、仓位结构

扫描开始时给这批 registry 行记同一个 cohort / group id。清理按 `env_fp` 整组：当前环境不拆；过时环境超出 N 组则最旧一组的 simulation 与归因目录一起删。

---

## 6. 指纹怎么用

不改身份规则，不把设置指纹升成父级。缺的是「这几号是同一批」的索引。

| 指纹 | 里面有什么 | 归因怎么用 |
|------|------------|------------|
| `env_fp` | 策略路径、NTQ 版本、DB 类型、hooks 源码、data contract 映射文件哈希 | group 键 |
| `execute_fp` | 白名单 settings（含 `simulation` 区间）+ 排序后的股票池 | 用「快照 + 一格 inputs 变更」算目标指纹，在 group 里命中 |

`meta` / `is_enabled` / `scanner` 等本来就不进 `execute_fp`。

指纹锁不住的是库里的行情内容：合约映射文件没变、K 线却被重新导入时，同一对指纹仍会命中旧 version。第一期当作已知限制，不为此再拆一枚指纹。

---

## 7. 两类可解释量：自动 vs `capture`

归因都该收，但来源不同。

| 你要解释的 | 自动？ | 从哪来 |
|------------|--------|--------|
| 阈值扫 20 / 25 / 30 账户怎么变 | 是 | 各 version 的 `effective_settings.json`（inputs 声明路径） |
| 这笔买入时 RSI / MACD 是多少 | `settings.data` 声明了该列则是；否则要 `capture` | 该笔 as-of snapshot |
| 钩子里自己算的、未声明的量 | 否 | 必须 `capture` |

**设置参数**不需要、也不应该再 `capture` 一遍。它们在单次运行里是常数，写进 snapshot 没有新信息。参数战役只读**共用展格**（及默认轴）上的设置路径。旋钮写死在 `strategy.py`、不在 settings 中，现有产物里没有这个值，也扫不到；要参与归因，就把它放进 settings。

**实时指标**（机会 A 的 RSI 是 17、机会 B 是 19）不在 settings 里。正确做法不是寄希望于用户记得 `capture`：

- 机会成立的那一根，留下 **as-of 当日那一片**：base 那根 K 线（含已声明指标列），再加上当时其它已声明数据的最后一行
- 用户 `capture` 合并进去，同名以用户为准
- 不要整段历史，也不要事后再去行情库里猜

这只对之后的 Run 生效。已经跑完、snapshot 里没有这些列的旧 version，补不出当日读数。

当前代码：命中时把 **as-of 当日那一片** 写入 `signal_snapshot`。用户 `capture` 同名覆盖，且只应收钩子自己算的量。滚动验证读同一份 `attribution.py` 里的 `rolling.windows`（CLI `sw`），报告仍写在 `rolling/`，不和参数战役混表。口径未定。

---

## 8. 模块边界

```text
战役入口 Analyzer.attribute_* / CLI sea|spa|soa
  → strategy（指纹缓存 / 主号校验 / 副本 allocate / 复用 Strategy.simulate）
  → modules.analysis（分桶、相关、对照；无业务、无 I/O）
```

战役格子的「每个因子贡献了多少」分两章，写在同一份报告里，不要为此跑两次同一层 CLI：

- **参数贡献度（有/无）**：某一格把该位置写成 `None`（关），对照开着的格子。基准是关掉的那一格。
- **参数敏感度（取值）**：只在开着的格子之间比数字；基准是开着的第一套，不是全局表头（表头若是关着的，不算敏感度基准）。

一次只动一个旋钮的行才能算到那个因子头上；一套里同时改多个旋钮就拆不开。报告再补三件不靠 ML 的对照（写在敏感度章）：按旋钮取值排序的边际、格子铺满矩形才出的交叉表、旋钮在机会层和账户层是否同向。OLS / 逻辑回归 / XGB+SHAP 是给单笔机会用的（要几十到几百行）；几套回测不够拟合，战役不算这些。

- **不要**并进 `modules.analysis`：它不能调度、不能读盘、不能开 N 次回测
- **不要**再开一个和 strategy 平级的 `modules.attribution`：group、指纹、version 缓存、枚举落盘都已经在 strategy；拆出去只会再实现一遍
- **不要**做成四层后面的第五层回测：扫描是旁边一种跑法，每个 version 仍按原来的层往下跑
- **不要**把这次扫描塞回「跑一次回测顺便归因」的开关

`Analyzer` 继续担任归因的职责：`attribute_*` 读 group / 展开**共用** `inputs`；`run` 仍是切片库。CLI 只决定补哪一层产物与总结哪一层指标（§0.2–0.3）。

---

## 9. 本轮明确不做

- 战役 BFF / UI 入口（CLI `sea` / `spa` / `soa` / `sw` 已接）
- 在 `sea` 时预跑价格 / 组合「以防万一」（与懒执行相悖）

---

## 10. `attribution.py`

单独文件，与 `settings.py` 并列。Workbench 保存 settings 时不要改它。不进 `execute_fp` / `env_fp`。

参数战役配置见 [ATTRIBUTION_INPUTS.md](./ATTRIBUTION_INPUTS.md)：声明共用对照轴（每轴 `{"values": [...]}`），`cross` 默认 `false`；`cross: true` 为笛卡尔积（上限 128 格）。**不使用** `overlays` / `matrix`。

没有顶层 `mode`。**不要写 `steps`**——层由 CLI（`sea` / `spa` / `soa`）决定执行深度与报告因变量，**不**决定「另一套副本」。轴只写顶层 `inputs`。`rolling.windows` 是另一项任务，可与参数战役写在同一文件，由 `sw` 使用，口径未定。战役 `inputs`、`rolling.windows` 不能都空到无事可做。不要写 `versions` 选号、分层 inputs 或 `shap`。

目标形态（一份共用轴）：

```python
attribution = {
    "inputs": {
        "rsi_oversold_threshold": {"values": [20, 25]},
        "max_pe_percentile": {"values": [30, None]},
        "stop_loss": {
            "values": [
                None,
                {"stages": [{"ratio": -0.2, "close_invest": True}]},
            ],
        },
        "opportunity_merge_gap": {"values": [1, 3]},
        "max_portfolio_size": {"values": [10, 20]},
    },
    "cross": False,
    "rolling": {
        "windows": [
            {"start": "20230101", "end": "20231231"},
            {"start": "20240101", "end": "20241231"},
        ],
    },
}
```

过渡：轴仍可写在 `enumerate` / `price_factor` / `portfolio` 块的 `inputs` 下（便于阅读或默认轴归属），但 **`sea` / `spa` / `soa` 展格必须合并为同一套副本身份**；禁止只展「当前 CLI 对应块」。

上例 oaat 下：基准格 + 各轴相对基准的取值变体（与基准相同的去重）。`sea` 只为这些身份补枚举；随后 `spa` / `soa` 对**同一批身份**再补价格 / 组合。若 `"cross": True` 则笛卡尔积。每格在需要补跑时调用 `Strategy.simulate` 到当前层（同身份复用；对照格写 `{vid}-{r}`）。待跑格数与粗算数据量超过阈值时警告或拒绝，见 INPUTS §6。

### 展格后如何作用在 effective 上

快照 = 当前 `settings.py` 抽出的 **effective**。每一格 = 快照 + 本格路径取值 → 再走一遍 `to_usable` / `extract_execute_settings`，和普通 Run 同一套身份。

- 只允许 `execute_fp` 白名单块。写 `meta` / `scanner` / `is_enabled` 报错。
- **自动带当前 settings 一格当基准**（无路径变更，不写进 `attribution.py`）。
- **oaat 下一格只变更声明的那一个路径**；未写到的兄弟键（只改 `stop_loss` 时的 `take_profit`）留在快照里。`cross` 下一格带齐各轴在该组合上的取值。
- **动到 effective 的哪个位置，就换掉那个位置上的整份值**。不要字段级深合并：不能只写一档的 `ratio` 却继承同一档里的 `close_invest`。
- `core` 里各 key 各算各的位置，可以只改 `rsi_oversold_threshold`。
- **省略路径 = 继承快照；写成 `None` = 关掉这个位置。** 空 `stages: []` 仍然非法。关止损时留着止盈（不要两头一起关，否则只剩期末强平）。框架不会替 `strategy.py` 跳过 `core` 门槛；作者要把 `None` 当成跳过。`None` 会换 `execute_fp`，和改数字一样是新号。
- 分类看 **effective 在声明路径上的值**。
- **list 整段替换。** 写了 `stop_loss.stages` 就换整张 stages；每一档必须把 effective 里该种对象的字段写全。`goal` 轴的 `values` 规则见 INPUTS §4.3。

滚动窗口写在 `attribution.rolling.windows`，不另开 `rolling.py`。CLI `sea`/`spa`/`soa`/`sw` 的 `-f` 与 `s -f` 相同：回测层 `ignore_cache`，同指纹写回原号（副本同理）。

---

## 11. 实现差距

基础设施（共用身份、懒执行链、顶层 inputs）已对齐 §0。  
**产品扫描形态**的差距与实施顺序以 [ATTRIBUTION_SWEEP.md](./ATTRIBUTION_SWEEP.md) §7–8 为准（排名 + 曲线、多档默认、`joint_sweep`、UI 等）。

相关现行契约：[VERSIONING.md](../VERSIONING.md)、[DECISIONS.md](../DECISIONS.md)、analyzer [BOUNDARY.md](../../core/engines/analyzer/docs/BOUNDARY.md)、[ATTRIBUTION.md](./ATTRIBUTION.md)、[ATTRIBUTION_SWEEP.md](./ATTRIBUTION_SWEEP.md)、[ATTRIBUTION_INPUTS.md](./ATTRIBUTION_INPUTS.md)。
