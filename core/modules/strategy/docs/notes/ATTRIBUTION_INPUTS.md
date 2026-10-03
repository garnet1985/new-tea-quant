# 归因自变量、因变量与配置

**状态：** 口径已锁定（2026-10-03）。替换原 `overlays` / `matrix` 写法；不保留旧配置兼容。战役展格与指纹见 [ATTRIBUTION_CAMPAIGN.md](./ATTRIBUTION_CAMPAIGN.md)。层内要回答的问题见 [ATTRIBUTION.md](./ATTRIBUTION.md)、[ATTRIBUTION_ENUM.md](./ATTRIBUTION_ENUM.md)、[ATTRIBUTION_PRICE.md](./ATTRIBUTION_PRICE.md)、[ATTRIBUTION_PORTFOLIO.md](./ATTRIBUTION_PORTFOLIO.md)。展示见 [ATTRIBUTION_PRESENT.md](./ATTRIBUTION_PRESENT.md)。

**一句话：** 用户在 `attribution.py` 里按回测层声明要变更的 settings 路径及取值列表；系统按该层固定的结果指标做对照解释。默认每次只改一个路径（oaat）；`cross: true` 时才做多路径笛卡尔积。

---

## 1. 三类数据（不要混称「参数」）

| 名称 | 是什么 | 是否生成对照回测格 | 来源 |
|------|--------|-------------------|------|
| 可对照 settings 路径 | 单次 version 内为常数的配置项（如 `core.max_pe_percentile`、`goal.stop_loss`） | 是（自变量） | `settings.py` → 各格 `effective_settings` |
| 现场观测 | 某笔机会成立当时的量（如当日 RSI、用户 `capture` 字段） | 否；`capture` 即表示要解释，无需再配 | `signal_snapshot` / `capture` |
| 结果指标 | 回测结束后的汇总与明细统计 | 否（因变量） | `overall_report`、`entities` 等 |

说明：

- 解释「某过滤条件或阈值对机会数量/分布的影响」时，变更的是 **settings 路径上的阈值或开关**，不要求用户 `capture` 当场特征值（例如不必 `capture` 每笔的 PE 分位，也能对照 `core.max_pe_percentile`）。
- `capture` 表示用户希望把额外现场量纳入观测或逐笔解释；**不能**代替 settings 路径上的取值列表来展开多格回测。
- 结果指标是解释目标，不要写进 `inputs` 当可扫轴。

---

## 2. 每层固定的结果指标（output，用户不配置）

用户不配置「要解释什么」。跑哪一层 CLI（`sea` / `spa` / `soa`），就用该层下表。跨格对照时，对各格使用**同一套**指标做差值。

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
| `edge` | 去噪后等权机会账的胜率、平均 ROI、盈亏比 |
| `profit_concentration` | 利润是否集中在少数笔 / 少数票 |
| `exit_profit` | 各出场原因对总利润的贡献 |
| `denoising_bias` | 合并与可交易性过滤去掉的样本是否系统性更差 |

### 2.3 portfolio（`soa`）

| 键 | 要回答的问题 |
|----|--------------|
| `attrition` | 价格层完成笔数到组合成交的折损；利用率、满槽 |
| `bought_vs_missed` | 买到与漏掉的机会质量差 |
| `allocation_structure` | 仓位集中度、回撤段同时亏损的持仓结构 |

滚动窗口仍走 `sw` 与 `attribution.rolling`，不并入上表 `inputs`。

---

## 3. 每层默认的可对照路径（default inputs）

未在本层声明 `inputs`（或 `inputs` 为空）时，若默认路径在当前 effective 中可解析，系统自动加入默认对照。一旦本层声明了非空 `inputs`，则**只扫声明的轴**，不再自动追加未写的默认轴。

| 层 | 默认轴 | 默认取值策略 |
|----|--------|--------------|
| enumerate | `goal.stop_loss`、`goal.take_profit`（整段结构）；`core` 下标量键 | 止损/止盈：`[当前整段, None]`；`core` 过滤类：`[当前值, None]`；`core` 信号阈值：`[当前值, 邻近一档]`（邻近规则实施时固定） |
| price_factor | `simulation.price.opportunity_merge_gap` | `[当前值, 更宽一档, 更窄一档]`（档位实施时固定） |
| portfolio | `portfolio.allocation.max_portfolio_size`、`max_weight_per_stock`、`mode`（取值个数少时） | 槽位：`[当前值, 更大一档]`；`mode`：当前与另一候选 |

不默认扫：`fees`、`data`、回测区间、`rolling`。

**钩子止损 / 止盈**（如 `is_stop_loss` / `is_take_profit` 自定义，而非 settings 中可替换的 `stages` 结构）：该轴标记为不可扫，不生成取值列表对照；报告仅做单版出场诊断。用户若对该轴配置了标量 `values`，校验报错。若需「钩子 vs 固定 stages」对照，用户在 `values` 中给出完整结构（或 `None`），不得使用裸数字 ratio 列表。

**缺省与报错：**

- 未写该层 `inputs`：使用上表默认轴；若默认轴均不可用，则只跑基准格并做单版诊断，不因「未配置」失败。
- 路径不存在、`values` 非法、钩子轴却写了不可解析的标量：校验失败。
- 配置错误与「使用默认」分开处理。

---

## 4. 配置格式（唯一合法写法）

文件：策略目录下 `attribution.py`，导出 `attribution` dict。不进 `execute_fp` / `env_fp`。Workbench 保存 `settings.py` 时不要改本文件。

### 4.1 形状

```python
attribution = {
    "enumerate": {
        "inputs": {
            "stop_loss": {
                "values": [
                    None,
                    {"stages": [{"ratio": -0.2, "close_invest": True}]},
                ],
            },
            "max_pe_percentile": {"values": [None, 10, 30]},
            "rsi_oversold_threshold": {"values": [20, 25, 30]},
        },
        "cross": False,
    },
    "price_factor": {
        "inputs": {
            "opportunity_merge_gap": {"values": [1, 3, 5]},
        },
    },
    "portfolio": {
        "inputs": {
            "max_portfolio_size": {"values": [10, 20]},
        },
    },
    "rolling": {
        "windows": [
            {"start": "20230101", "end": "20231231"},
        ],
    },
}
```

规则：

- 参数战役只认按层块下的 `inputs`（及可选 `cross`）。**不认** `overlays`、`matrix`。
- 每个轴的取值声明**只有** `{"values": [...]}` 一种形式。不提供 `range` / `step` 配置键（若工具生成列表，写入前展开为 `values`）。
- `cross` 默认 `false`（oaat）。`true` 时对本层 `inputs` 各轴做笛卡尔积。
- 现场量（`capture` / `signal_snapshot`）**不必**在 `attribution.py` 再声明：用户 `capture` 了即视为要纳入逐笔解释；与 `inputs` 展格无关。
- `versions` 选号、`rolling.windows` 滚动仍见 [ATTRIBUTION_CAMPAIGN.md](./ATTRIBUTION_CAMPAIGN.md)；与参数战役可同文件，由不同 CLI 使用。
- 不要写 `steps`；层由 CLI 决定。跑 `sea` 时只使用 `enumerate` 块（加默认轴）；`spa` / `soa` 同理。

### 4.2 短名与路径

层内短名映射到 settings 路径（实施时维护登记表）。示例：

| 短名 | 路径 |
|------|------|
| `stop_loss` | `goal.stop_loss` |
| `take_profit` | `goal.take_profit` |
| `max_pe_percentile` | `core.max_pe_percentile` |
| `rsi_oversold_threshold` | `core.rsi_oversold_threshold` |
| `opportunity_merge_gap` | `simulation.price.opportunity_merge_gap` |
| `max_portfolio_size` | `portfolio.allocation.max_portfolio_size` |

也允许直接写点号路径。短名与路径指向同一位置时不得重复声明冲突的 `values`。

### 4.3 `goal` 轴的取值

`goal.stop_loss` / `goal.take_profit` 的每个 value 必须是：

- `None`：关闭该位置；或
- 与 effective 兼容的**整段结构**（含完整 `stages` 等字段）。

**list 整段替换**：写入 `stages` 即替换整张 stages；每一档字段写全，不做字段级深合并。

**单段数字简写（可选）：** 当且仅当当前 effective 为单段且存在 `ratio` 时，允许 `values` 中出现数字（如 `-0.2`），解析时包成与当前同结构的单段对象。多段或钩子：禁止裸数字，校验失败。

### 4.4 展格后如何作用在 effective 上

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

上例去重后一般为 **5** 次：基准 + rsi∈{25,30} + pe∈{None,10}。

公式（去重前）：`1 + Σ_轴 (该轴 values 个数)`；与基准相同的格合并。

### 5.2 cross（`cross: true`）

各轴 `values` 笛卡尔积。上例 **3 × 3 = 9** 种组合（去重后按 effective 计）。

公式：`Π_轴 |values|`（再按身份去重）。

笛卡尔积硬上限 **128** 格（与历史 matrix 上限相同）。超过则校验失败。

报告主路径解释 **oaat** 单路径贡献。`cross` 用于路径同时变更时的交叉对照，须显式打开。

---

## 6. 成本闸

当前战役 execute **按格串行**调用 `Strategy.simulate`，总耗时近似随待跑格数线性增加。

在展格之后、执行之前计算：

1. **待跑格数 `N`**：展开并按身份去重后，仍需新 simulate 的格数（已命中可复用 version 的不计）。
2. **粗算 K 线量级**（不查数据库）：
   - 回测日历跨度（settings 或任务区间）→ 估算交易日数；
   - 标的规模：watch_list / 池规模，缺失时用保守默认；
   - base 数据频度（如日 K）→ 每标的 bars 约等于交易日数；
   - `bars_cost ≈ N × 标的数 × 每标的 bars`。

| 档位 | 行为 |
|------|------|
| 软警告 | `N` 或 `bars_cost` 超过软阈值：提示串行、建议减少 `values` 或关闭 `cross`；UI 可要求确认 |
| 硬停 | `N > 128`，或 `bars_cost` 超过硬阈值：拒绝执行 |

阈值具体数字实施时写入常量；估不准时宁可硬停。

---

## 7. 报告与轴的对应

- 某结果指标章节应优先引用**与该问题相关**的路径变更（例如出场结构章节优先 `goal` 轴；机会数量章节优先 `core` 过滤/信号轴）。
- 禁止把无关路径的差值默认写进该章节主结论。
- 无对照格（仅基准）时：只做单版诊断；不编造「若改为某值」的百分比。

---

## 8. 实施约束

- 遵守仓库根目录 `CODE_STYLE.md`。
- 在现有 `campaign/config`、`plan`、`execute`、报告家族命名上**直接替换**为按层 `inputs`；删除 `overlays` / `matrix` 配置解析与双表等价逻辑，**不**保留「读旧键再翻译」的兼容层。
- 样例策略 `attribution.py` 与测试随实施一并改为新 schema。
- 本文件锁定口径；代码未改前 CLI 仍可能只认旧键——以实施 PR 落地为准。

---

## 9. 明确不做

- 旧 `overlays` / `matrix` 配置的自动升级或静默兼容
- 用 `capture` 字段名自动生成 settings 对照轴
- 无对照格的反事实百分比
- 把滚动窗口并进层内 `inputs` 笛卡尔积
