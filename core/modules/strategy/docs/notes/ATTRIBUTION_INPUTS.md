# 归因自变量、因变量与配置

**状态：** 口径修订（2026-10-03）。与 [ATTRIBUTION_CAMPAIGN.md](./ATTRIBUTION_CAMPAIGN.md) §0、[ATTRIBUTION_SWEEP.md](./ATTRIBUTION_SWEEP.md) 对齐：共用扫描点 + 单因素多档为主 + 可选联合扫。

**一句话：** 用户声明共用 `inputs`（每轴多档）；默认单因素扫描；可选 `joint_sweep`；`sea`/`spa`/`soa` 对同一批点懒补后，用该层指标画曲线与排名。全轴 `cross: true` 不推荐当默认。

---

## 0. 与战役概念的衔接（必读）

1. **自变量决定副本身份，不决定「哪一层私有的格子」。**  
   改止损、改因子、改 merge_gap、改槽位，都是同一战役里的「如果」分支；三层归因共用这些 version 号。
2. **CLI 决定执行深度与因变量，不另起展格。**  
   `sea` 只补枚举；`spa` 再补价格；`soa` 再补组合。管道形状相同，见 CAMPAIGN §0.3。
3. **错误写法：** 「跑 `spa` 时只展开 `price_factor.inputs`、跑 `sea` 时只展开 `enumerate.inputs`」。那会变成三套副本，本末倒置。

---

## 1. 三类数据（不要混称「参数」）

| 名称 | 是什么 | 是否生成对照回测格 | 来源 |
|------|--------|-------------------|------|
| 可对照 settings 路径 | 单次 version 内为常数的配置项（如 `core.max_pe_percentile`、`goal.stop_loss`） | 是（自变量） | `settings.py` → 各格 `effective_settings` |
| 现场观测 | 某笔机会成立当时的量（如当日 RSI、用户 `capture` 字段） | 否；`capture` 即表示要解释，无需再配 | `signal_snapshot` / `capture` |
| 结果指标 | 回测结束后的汇总与明细统计 | 否（因变量） | `overall_report`、`entities` 等 |

说明：

- 解释「某过滤条件或阈值对机会数量/分布的影响」时，变更的是 **settings 路径上的阈值或开关**，不要求用户 `capture` 当场特征值。
- `capture` 表示用户希望把额外现场量纳入观测或逐笔解释；**不能**代替 settings 路径上的取值列表来展开多格回测。
- 结果指标是解释目标，不要写进 `inputs` 当可扫轴。

---

## 2. 每层固定的结果指标（output，用户不配置）

用户不配置「要解释什么」。跑哪一层 CLI（`sea` / `spa` / `soa`），就用该层下表。跨格对照时，对各格使用**同一套**指标做差值——格来自**共用副本**，不是本层私有格子。

### 2.1 enumerate（`sea`）

| 键 | 要回答的问题 | 主要指标 |
|----|--------------|----------|
| `opportunity` | 变更 settings 后，机会数量如何变 | `total_opportunities` |
| `stock_distribution` | 机会在股票上的覆盖与分布如何变 | `trigger_ratio`、分桶、`top_bucket_ratio` |
| `dispersion` | 单票触发时间是否集中 | `cv`、`mean_gap`、`dispersion_conclusion` |
| `exit_quality` | 止损 / 止盈 / 过期占比及是否集中在少数票、少数月份 | `stop_loss_ratio`、`take_profit_ratio`、`expire_ratio`；基准版按票/按月 |
| `after_take_profit` | 止盈之后是否还有上涨空间 | 仅当 `goal` 为分档或动态止盈等可观测设置时；一档全平则标明不可测 |

范围句（报告必须带）：这是每笔机会独立走完目标的纸面结局，含重叠；不是价格层去重后的交易，也不是组合层资金。

### 2.2 price_factor（`spa`）

| 键 | 要回答的问题 |
|----|--------------|
| `edge` | 去噪后等权投一笔：能不能赚、赚得够不够（胜率、均收益、总盈亏、盈亏比、ROI 中位等） |
| `profit_concentration` | 利润是否集中在少数笔 / 少数票（留下的样本是否像普遍现象） |
| `exit_profit` | 各出场原因对总利润的贡献（只描述结构；不代算盈利区间） |

说明：

- 价格层**不做**「跳过的 vs 留下的」质量对比（近邻跳过是去重复，不是质量过滤）。
- **不做**系统代算「盈利区间 / MFE」；止盈止损空间由用户在 settings / 共用 `inputs` 里配置。`spa` 只对照各副本价格账上的结果指标。
- 因子 / 止损等轴若已在共用展格里，`spa` 应能在同一批副本的价格产物上读出胜率、均收益等差异——不是另开一套价格专用格子。
- `opportunity_merge_gap` 是可选共用轴，不是「价格层私有战役」的主轴。详见 [ATTRIBUTION_PRICE.md](./ATTRIBUTION_PRICE.md)。

### 2.3 portfolio（`soa`）

| 键 | 要回答的问题 |
|----|--------------|
| `attrition` | 价格层完成笔数到组合成交的折损；利用率、满槽 |
| `bought_vs_missed` | 买到与漏掉的机会质量差 |
| `allocation_structure` | 仓位集中度、回撤段同时亏损的持仓结构 |

组合层主问题是资金管理；报告结论优先引用分配类轴。想法轴（`core.*` / `goal.*`）仍在共用副本上时，组合产物也可以对照，但不要把账户差再讲成一遍 PE 贡献（见 PORTFOLIO）。

滚动窗口仍走 `sw` 与 `attribution.rolling`，不并入上表 `inputs`。

---

## 3. 默认对照轴（合并进共用展格）

未声明任何战役 `inputs`（或合并后为空）时，若下列默认路径在当前 effective 中可解析，系统自动加入默认对照。一旦用户声明了非空 `inputs`（顶层或各层块合并后非空），则**只扫声明的轴**，不再自动追加未写的默认轴。

| 来源（便于阅读） | 默认轴 | 默认取值策略 |
|------------------|--------|--------------|
| 想法 / 枚举侧 | `goal.stop_loss`、`goal.take_profit`（整段结构）；`core` 下标量键 | 止损/止盈：`[当前整段, None]`；`core` 过滤类：`[当前值, None]`；`core` 信号阈值：`[当前值, 邻近一档]` |
| 价格去噪（可选） | `simulation.price.opportunity_merge_gap` | `[当前值, 更宽一档, 更窄一档]` |
| 资金分配 | `portfolio.allocation.max_portfolio_size`、`max_weight_per_stock`、`mode`（取值个数少时） | 槽位：`[当前值, 更大一档]`；`mode`：当前与另一候选 |

不默认扫：`fees`、`data`、回测区间、`rolling`。

**已否定的规则：** 「价格层禁止对照 `goal.*` / `core.*`」。那是「每层私有副本」模型下的产物。共用副本后：这些轴出现在展格里时，`spa` / `soa` 同样使用对应 version 的价格 / 组合产物做对照；只是报告章节仍只把**与该问题相关**的轴写进主结论（§7）。

**钩子止损 / 止盈**（如 `is_stop_loss` / `is_take_profit` 自定义，而非 settings 中可替换的 `stages` 结构）：该轴标记为不可扫，不生成取值列表对照；报告仅做单版出场诊断。用户若对该轴配置了标量 `values`，校验报错。若需「钩子 vs 固定 stages」对照，用户在 `values` 中给出完整结构（或 `None`），不得使用裸数字 ratio 列表。

**缺省与报错：**

- 未写战役 `inputs`：使用上表默认轴（合并后）；若默认轴均不可用，则只跑基准格并做单版诊断，不因「未配置」失败。
- 路径不存在、`values` 非法、钩子轴却写了不可解析的标量：校验失败。
- 配置错误与「使用默认」分开处理。

---

## 4. 配置格式

文件：策略目录下 `attribution.py`，导出 `attribution` dict。不进 `execute_fp` / `env_fp`。Workbench 保存 `settings.py` 时不要改本文件。

### 4.1 目标形状（一份共用轴）

```python
attribution = {
    "inputs": {
        "stop_loss": {
            "values": [
                None,
                {"stages": [{"ratio": -0.2, "close_invest": True}]},
            ],
        },
        "max_pe_percentile": {"values": [None, 10, 30]},
        "rsi_oversold_threshold": {"values": [20, 25, 30]},
        "opportunity_merge_gap": {"values": [1, 3, 5]},
        "max_portfolio_size": {"values": [10, 20]},
    },
    "cross": False,
    # 可选：仅指定轴子集笛卡尔（与全轴 cross 不同）
    "joint_sweep": [
        ["stop_loss", "take_profit"],
    ],
    "rolling": {
        "windows": [
            {"start": "20230101", "end": "20231231"},
        ],
    },
}
```

- `joint_sweep`：每组 2～3 个轴；轴须已在 `inputs` 声明 `values`；在默认单因素格子之外**额外**跑该子集笛卡尔。  
- 全轴 `cross: true` 时忽略 `joint_sweep`（并告警）。

### 4.2 过渡形状（按层分块存放轴）

仍允许把轴写在 `enumerate` / `price_factor` / `portfolio` 块下，便于阅读或标注默认轴归属：

```python
attribution = {
    "enumerate": {
        "inputs": {
            "rsi_oversold_threshold": {"values": [20, 25]},
            "stop_loss": {
                "values": [
                    None,
                    {"stages": [{"ratio": -0.2, "close_invest": True}]},
                ],
            },
        },
        "cross": False,
    },
    "price_factor": {
        "inputs": {
            "opportunity_merge_gap": {"values": [1, 3]},
        },
    },
    "portfolio": {
        "inputs": {
            "max_portfolio_size": {"values": [10, 20]},
        },
    },
}
```

**硬规则：** 无论轴写在哪一块，`sea` / `spa` / `soa` **必须合并为同一套副本身份**再 plan / execute。`cross` 若分块出现，以战役级一次展格为准（建议只在一处声明；冲突则校验失败）。

规则摘要：

- 参数战役只认 `inputs`（顶层或各层块）、可选 `cross`、可选 `joint_sweep`。**不认** `overlays`、`matrix`。
- 每个轴的取值声明**只有** `{"values": [...]}` 一种形式。
- `cross` 默认 `false`（单因素多档）。`true` 时对**合并后的**各轴做笛卡尔积（一般不推荐）。
- `joint_sweep` 为轴子集小矩阵；优先于「全轴 cross」用于交互排查。
- `shap`：价格层单笔 XGB+SHAP 附录，**默认 `false`**；需要时写 `shap: true`。
- 现场量不必在 `attribution.py` 再声明。
- `versions` 选号、`rolling.windows` 滚动仍见 [ATTRIBUTION_CAMPAIGN.md](./ATTRIBUTION_CAMPAIGN.md)。
- 不要写 `steps`；层由 CLI 决定执行深度与因变量，不决定另一套副本。

### 4.3 短名与路径

短名映射到 settings 路径（实施时维护登记表）。示例：

| 短名 | 路径 |
|------|------|
| `stop_loss` | `goal.stop_loss` |
| `take_profit` | `goal.take_profit` |
| `max_pe_percentile` | `core.max_pe_percentile` |
| `rsi_oversold_threshold` | `core.rsi_oversold_threshold` |
| `opportunity_merge_gap` | `simulation.price.opportunity_merge_gap` |
| `max_portfolio_size` | `portfolio.allocation.max_portfolio_size` |

也允许直接写点号路径。短名与路径指向同一位置时不得重复声明冲突的 `values`。

### 4.4 `goal` 轴的取值

`goal.stop_loss` / `goal.take_profit` 的每个 value 必须是：

- `None`：关闭该位置；或
- 与 effective 兼容的**整段结构**（含完整 `stages` 等字段）。

**list 整段替换**：写入 `stages` 即替换整张 stages；每一档字段写全，不做字段级深合并。

**单段数字简写（可选）：** 当且仅当当前 effective 为单段且存在 `ratio` 时，允许 `values` 中出现数字（如 `-0.2`），解析时包成与当前同结构的单段对象。多段或钩子：禁止裸数字，校验失败。

### 4.5 展格后如何作用在 effective 上

快照 = 当前 `settings.py` 的 effective。每一对照格 = 快照 + 本格要改的路径取值 → 再走 `to_usable` / `extract_execute_settings`，与普通 Run 同一套身份。

- 只允许变更 `execute_fp` 白名单块；写 `meta` / `scanner` / `is_enabled` 报错。
- 自动带当前 settings 一格为基准（空变更，不写进 `attribution.py`）。
- 未出现在本格变更里的路径继承快照；写成 `None` = 关闭该位置。
- 分类与对照看 **effective 在声明路径上的值**。

---

## 5. 展开方式与回测次数

设基准为当前 settings。例：

- `rsi_oversold_threshold`: `[20, 25, 30]`
- `max_pe_percentile`: `[None, 10, 30]`
- 基准：`rsi=20`，`pe=30`

### 5.1 oaat（`cross: false`，默认）

每格 = 基准 + **只改一个轴上的一个 value**。与基准 effective 相同的格去重，不重复回测。

上例去重后一般为 **5** 次身份：基准 + rsi∈{25,30} + pe∈{None,10}。

公式（去重前）：`1 + Σ_轴 (该轴 values 个数)`；与基准相同的格合并。

**层代价：** `sea` 只为待补身份跑枚举；同一批身份上再跑 `spa` / `soa` 时，只补缺的价格 / 组合，不重新定义另一套格子。

### 5.2 cross（`cross: true`）

各轴 `values` 笛卡尔积。上例 **3 × 3 = 9** 种组合（去重后按 effective 计）。

公式：`Π_轴 |values|`（再按身份去重）。

笛卡尔积硬上限 **128** 格（与历史 matrix 上限相同）。超过则校验失败。

报告主路径解释 **oaat** 单路径贡献。`cross` 用于路径同时变更时的交叉对照，须显式打开。

---

## 6. 成本闸

当前战役 execute **按格串行**调用 `Strategy.simulate`，总耗时近似随待跑格数 × 层深度增加。分层 CLI 的意义就是：调试想法时不要预跑价格 / 组合。

在展格之后、执行之前计算：

1. **待跑格数 `N`**：展开并按身份去重后，仍需新 simulate **本层**（及缺失上游）的格数（已命中可复用 version 的不计）。
2. **粗算 K 线量级**（不查数据库）：
   - 回测日历跨度（settings 或任务区间）→ 估算交易日数；
   - 标的规模：watch_list / 池规模，缺失时用保守默认；
   - base 数据频度（如日 K）→ 每标的 bars 约等于交易日数；
   - `bars_cost ≈ N × 标的数 × 每标的 bars`（可按层再乘成本系数）。

| 档位 | 行为 |
|------|------|
| 软警告 | `N` 或 `bars_cost` 超过软阈值：提示串行、建议减少 `values` 或关闭 `cross`；UI 可要求确认 |
| 硬停 | `N > 128`，或 `bars_cost` 超过硬阈值：拒绝执行 |

阈值具体数字实施时写入常量；估不准时宁可硬停。

---

## 7. 报告与轴的对应

- 某结果指标章节应优先引用**与该问题相关**的路径变更（例如出场结构章节优先 `goal` 轴；机会数量章节优先 `core` 过滤/信号轴；资金折损优先 `portfolio.allocation.*`）。
- 禁止把无关路径的差值默认写进该章节主结论。
- 无对照格（仅基准）时：只做单版诊断；不编造「若改为某值」的百分比。
- 共用副本上某轴对价格 / 组合指标的影响，由该层报告在相关章节引用；不是「该轴只能出现在某一层 CLI 的展格里」。

---

## 8. 实施约束

- 遵守仓库根目录 `CODE_STYLE.md`。
- 在现有 `campaign/config`、`plan`、`execute`、报告家族上改为**共用展格**；删除「按 CLI 只展本层块」的行为。
- 校验：**删除**「`spa` 禁止 `goal.*` / `core.*`」类规则；改为共用轴合法性 + 钩子不可扫等真实约束。
- 样例策略 `attribution.py` 与测试随实施一并调整（可先保留分块写法，但测试必须断言三 CLI 身份集合一致）。
- 本文件与 CAMPAIGN §0 / §11 锁定口径；代码未改前行为以差距表为准。

---

## 9. 明确不做

- 旧 `overlays` / `matrix` 配置的自动升级或静默兼容
- 用 `capture` 字段名自动生成 settings 对照轴
- 无对照格的反事实百分比
- 把滚动窗口并进层内 `inputs` 笛卡尔积
- 各 CLI 各养各的副本身份集合
- 系统代用户探测「最大有利/不利偏移」以定义盈利区间（交给用户配置止盈止损；特殊探针另案）
