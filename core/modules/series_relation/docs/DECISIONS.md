# Series Relation — 设计与决策

**模块：** `modules.series_relation` · **版本：** `0.2.0`

**最低支持核心版本：** `>=0.5.0`

本文记录本模块的设计目标、方案思路与拍板决策。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 设计目标

多条 time series 并置比较：对齐呈现 + 可选关系摘要。与 analysis 分家：analysis 解释「一次策略 run」，本模块比较「多条外部/行情曲线」。实现时 Facade 拟为 `SeriesRelation`。

## 方案与思路

**扩展布局**：模块名 `modules.series_relation`；userspace 路径 `userspace/extensions/series_relation/<key>/`，与 `userspace/extensions/tags/<key>/` 同模式——先 `extensions`，再业务种 `series_relation`，再具体场景 `<key>`。

**选源**：仅 `meta.type == time_series` 的 data_key；`global` 选 field；`per_entity` 选 entity + field。

### Settings 草样

路径：

```text
userspace/extensions/series_relation/<key>/
  settings.py          # 本配置
  results/             # 跑批产物（实现期可再定是否放这里）
```

```python
settings = {
    "meta": {
        "key": "cn_index_vs_lpr",
        "display_name": "股指 vs LPR",
    },
    "series": [
        # 契约源（默认 source=data_key）
        {
            "data_key": "macro.lpr",
            "field": "lpr_1y",
            "label": "LPR 1Y",
            "transform": "none",             # none | returns；契约默认 none
        },
        # 回测产物源：只负责引入序列；和谁比由本 list 组合决定
        {
            "source": "strategy_sim",
            "strategy_key": "demo/regression/rsi/rsi_v1_baseline",
            # version 省略 → latest；钉死某次则写 "2"
            "layer": "portfolio",            # portfolio | price
            "metric": "equity",              # portfolio.equity | price.cum_exit_roi
            # "entity_id": "600199.SH",      # 仅 price.cum_exit_roi 可选单票
            "label": "策略组合权益",
            "transform": "returns",          # strategy_sim 默认 returns
        },
    ],
    "range": {
        "start_date": "",                    # 空 = 不裁；见窗口规则
        "end_date": "",
    },
    "normalize": "zscore",                   # none | zscore | minmax | index_100
    "fill": "none",                          # none | ffill（仅分析/可选呈现；默认 none）
    "analyze": True,                         # 是否写 findings / summary
}
```

**strategy_sim 装载：** 缺策略 / 缺 version / 缺该 layer 文件 / 0 点 → 整次硬失败（不换更旧 version）。  
分析样本不够 → 沿用 pairwise 软降级。`price.cum_exit_roi` 为事件曲线（按平仓累加 ROI），非盯市净值。

`max_series` **不出现在 settings**。模块内常量，例如：

```python
# core/modules/series_relation/.../constants.py（实现时）
MAX_SERIES = 6
```

#### 校验规则

1. `1 <= len(series) <= MAX_SERIES`（代码常量）。  
2. 每项必须有 `data_key`、`field`；契约必须是 `time_series`。  
3. `scope == per_entity` ⇒ `entity_id` 非空；`global` ⇒ 禁止或忽略 `entity_id`。  
4. `data_key` + `entity_id` + `field` 去重后不得重复。  
5. `normalize` / `fill` 枚举非法则拒跑。

#### 窗口 `range`

- 若起止都空：用各系列原始点的日期并集全长。  
- 若只裁一端：在并集上截断。  
- **不**为了凑齐窗口对缺失日造点（除非 `fill=ffill` 且仅作用于显式开启的用途）。

### 产物 schema（一步 run）

目录建议：`userspace/extensions/series_relation/<key>/results/`（或该目录下带 run 子层，实现期定）。

#### `meta.json`

```json
{
  "key": "cn_index_vs_lpr",
  "generated_at": "ISO-8601",
  "normalize": "zscore",
  "fill": "none",
  "max_series": 6,
  "range": {"start_date": "", "end_date": ""},
  "series": [
    {
      "id": "s0",
      "data_key": "stock.kline.daily",
      "entity_id": "000300.SH",
      "field": "close",
      "label": "沪深300",
      "scope": "per_entity",
      "point_count": 1200,
      "date_min": "20190102",
      "date_max": "20241008"
    }
  ]
}
```

`meta.max_series` 为跑批时生效的代码常量快照（便于复现），不是用户配置回写。

#### `series.json`（呈现主数据）

```json
{
  "calendar": ["20190102", "20190103", "20190201"],
  "series": [
    {
      "id": "s0",
      "label": "沪深300",
      "points": [
        {"date": "20190102", "raw": 3012.0, "norm": -0.12},
        {"date": "20190103", "raw": 3020.0, "norm": -0.10}
      ]
    },
    {
      "id": "s1",
      "label": "LPR 1Y",
      "points": [
        {"date": "20190201", "raw": 4.35, "norm": 1.02}
      ]
    }
  ]
}
```

约定：

- `calendar` = 裁剪后日期 **并集**（有序）。  
- 每条 `points` **只含有效观测**；UI 按 `points` 连线，不要按 `calendar` 强行插 null 再连（若宽表更好画，由前端自己 left-join）。  
- `raw` = 原字段值；`norm` = 归一化后（`normalize=none` 时与 `raw` 相同或省略 `norm`——实现时二选一，推荐始终带 `norm`，`none` 时 `norm=raw`）。

#### `summary.json`（CLI / 卡片）

```json
{
  "series_count": 2,
  "calendar_len": 1205,
  "pairwise": [
    {
      "a": "s0",
      "b": "s1",
      "overlap_n": 48,
      "reliable": true,
      "pearson": 0.21,
      "spearman": 0.18,
      "relation": "positive",
      "best_lag_days": -5,
      "best_lag_corr": 0.25,
      "lead": "b",
      "beta_b_on_a": 2.5,
      "beta_a_on_b": 0.4,
      "scale_r2": 0.81,
      "core": {
        "relation_text": "…",
        "lead_text": "…",
        "scale_text": "…"
      },
      "supplement": {
        "rolling": {"window": 60, "mean": 0.1, "recent": 0.2, "sign_flips": 1}
      },
      "warnings": []
    }
  ],
  "notes": [
    "统计在两两日期交集上计算；图为日期并集连点。"
  ]
}
```

口径：  
- `best_lag_days > 0` ⇒ a 领先 b；`< 0` ⇒ b 领先 a；`0` ⇒ 同步。  
- `beta_b_on_a` / `alpha_b_on_a`：原始值上 `B ≈ α + β·A`；β≈1 偏平移，|β| 离 1 远偏倍数。  
- `shape_ok=false`（相关弱）时先后/幅度文案降可信度。  
非因果。`analyze=false` 时可无 `pairwise`。

#### `findings.md`（可选，人读）

先写 **核心（相关 + 先后 + 幅度）**，再写 **补充（样本 / 滚动相关）**。不写因果。

### 两步产品（逻辑）

| 步 | 做什么 | 产物 |
|----|--------|------|
| 1 计算与呈现 | 拉数 → 并集日历 → 归一化 → `series.json` + `meta.json` | 必有 |
| 2 分析 | 交集上相关 / 简单滞后 → `summary.json` + `findings.md` | `analyze=true` |

CLI 可一次跑完；或 `run` / `analyze` 拆命令（实现期再定）。

### 边界

- **不做：** 因子挖掘、策略回测、在 CLI 里画真折线。  
- **复用：** 相关等统计可调 `modules.analysis` 已有原语；拉数走 DataManager / data_contract。  
- **与 analysis 分家：** analysis 解释「一次策略 run」；本模块比较「多条外部/行情曲线」。

### 待后续

- BFF / UI 读 `series.json` 画折线（后端完成后再做）。  
- `fill=ffill` 完整实现（需交易/自然日日历）；当前显式 ffill 仍不造点。  
- 示例场景 settings（需真实 data_key/field）。

---

## DEC-01：条数上限 MAX_SERIES = 6 为代码常量

**是什么：** 系列条数上限写死在代码里（`MAX_SERIES = 6`），不出现在用户 settings；超限拒跑，不静默截断。

**为什么选它：**

- 超过 6 条线的图可读性极差，限制是产品决策而非技术限制
- 代码常量避免用户误配——不是"可调参数"，是"产品边界"
- 超限显式拒跑比静默截断更安全

**放弃了什么：**

- **用户 settings 可调：** 高级用户可放宽 — 放宽后图不可读，违背产品意图

---

## DEC-02：时间轴用日期并集

**是什么：** 呈现用各系列日期的**并集**；统计用两两**交集**。

**为什么选它：**

- 并集保留所有观测点，图上能看出"哪天有数据哪天没有"
- 交集保证统计口径一致，避免因缺失日导致伪相关
- 呈现与统计分离，各自选最合适的口径

**放弃了什么：**

- **统一用交集：** 图上也只看交集 — 缺失日信息丢失，无法看出数据空洞
- **统一用并集：** 统计在并集上 — 缺失日填充会引入伪相关

---

## DEC-03：默认填充 fill: none

**是什么：** 默认不做 ffill；ffill 仅显式开启。

**为什么选它：**

- ffill 会造出"假数据"——缺失日被填成前值，误导分析
- 默认 none 保持数据诚实，用户显式开启才承担填值风险

**放弃了什么：**

- **默认 ffill：** 图上连线更平滑 — 数据诚实性优先于视觉平滑

---

## DEC-04：分析主轴 = 相关 + 领先滞后 + 幅度系数

**是什么：** 核心输出三件套：相关系数、最优滞后（lead/lag）、原始值 OLS β；补充样本门槛与滚动相关。

**为什么选它：**

- 这三件回答"像不像、谁领先、差几倍"——用户最关心的三个问题
- 滚动相关与样本门槛作为补充，不喧宾夺主

**放弃了什么：**

- **因果推断（Granger 等）：** 更"高级" — 本模块定位是描述关系，不做因果

---

## DEC-05：产物形状 = 每条系列一个 points 数组

**是什么：** `series.json` 每条系列独立 `points` 数组，非宽表。

**为什么选它：**

- 稀疏数据天然适配——每条系列只写有观测的日期
- 前端按 points 连线即可，不需要处理 null 占位

**放弃了什么：**

- **宽表（每行一个日期）：** 对齐整齐 — 稀疏数据下大量 null，存储与传输浪费

---

## DEC-06：本波无 BFF / UI

**是什么：** 模块只落盘 JSON，CLI 打印摘要与路径；前端可视化后端完成后再做。

**为什么选它：**

- 先把数据契约与计算跑通，UI 后续迭代
- 避免一次性做大功能导致延期

**放弃了什么：**

- **一步到位含 UI：** 用户体验完整 — 开发周期长，且 UI 设计需后端稳定后才能定

---

## DEC-07：CLI 缩写 srel（避开 sr）

**是什么：** CLI 命令 `series_relation`，缩写 `srel`；不用 `sr` 因为已被 strategy_rolling 占用。

**为什么选它：**

- 避免缩写冲突导致命令歧义

**放弃了什么：**

- **抢占 sr：** 更短 — 与现有命令冲突

---

## DEC-08：最优滞后基于去趋势收益率计算

**是什么：** 最优滞后（best_lag）在去趋势后的收益率上计算 CCF，不归一化水平值。

**为什么选它：**

- 归一化水平值高度自相关，CCF 结果接近噪音
- 去趋势收益率更贴近真实领先滞后关系

**放弃了什么：**

- **水平值 CCF：** 实现简单 — 自相关导致结果不可信，误导用户

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
