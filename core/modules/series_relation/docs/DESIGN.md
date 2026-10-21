# SeriesRelation — 设计

**版本：** `0.1.0`（设计稿；实现未开始）

多条 time series 并置比较：对齐呈现 + 可选关系摘要。  
相关约定见下文 settings / 产物；实现时 Facade 拟为 `SeriesRelation`。

---

## 已拍板

| 项 | 决定 |
|----|------|
| 模块名 | `modules.series_relation` |
| userspace 路径 | `userspace/extensions/series_relation/<key>/`（与 tags / adapters 同级的一类扩展） |
| 选源 | 仅 `meta.type == time_series` 的 data_key；`global` 选 field；`per_entity` 选 entity + field |
| 条数上限 | **代码常量**（建议 `MAX_SERIES = 6`），不进用户 settings；超限拒跑（不静默截断） |
| 时间轴 | **日期并集**；各系列只在自有观测日有值；折线按系列连接自身有效点 |
| 默认填充 | `fill: none`（不做 ffill）；ffill 仅显式开启 |
| 统计口径 | 两两 **交集**；与图的并集分开 |
| 分析主轴 | **核心**：相关 + 领先滞后 + **幅度系数（原始值 OLS β）**；**补充**：样本门槛、滚动相关 |
| 产物形状 | 每条系列一个 `points` 数组（非宽表） |
| 呈现 | 模块落盘 JSON；CLI 打印摘要 + 路径；**本波无 BFF/UI**（后端完成后再做） |
| CLI | `series_relation` / 缩写 `srel`（`sr` 已被 strategy_rolling 占用） |

---

## Settings 草样

路径：

```text
userspace/extensions/series_relation/<key>/
  settings.py          # 本配置
  results/             # 跑批产物（实现期可再定是否放这里）
```

与 `userspace/extensions/tags/<key>/` 同模式：先 `extensions`，再业务种 `series_relation`，再具体场景 `<key>`。

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
            "strategy_key": "demo/regression/rsi/rsi_v1_baseline",  # 推荐 meta.key；也可用相对路径（别名 strategy）
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

### 校验规则

1. `1 <= len(series) <= MAX_SERIES`（代码常量）。  
2. 每项必须有 `data_key`、`field`；契约必须是 `time_series`。  
3. `scope == per_entity` ⇒ `entity_id` 非空；`global` ⇒ 禁止或忽略 `entity_id`。  
4. `data_key` + `entity_id` + `field` 去重后不得重复。  
5. `normalize` / `fill` 枚举非法则拒跑。
### 窗口 `range`

- 若起止都空：用各系列原始点的日期并集全长。  
- 若只裁一端：在并集上截断。  
- **不**为了凑齐窗口对缺失日造点（除非 `fill=ffill` 且仅作用于显式开启的用途）。

---

## 产物 schema（一步 run）

目录建议：`userspace/extensions/series_relation/<key>/results/`（或该目录下带 run 子层，实现期定）。

### `meta.json`

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

### `series.json`（呈现主数据）

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

### `summary.json`（CLI / 卡片）

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

### `findings.md`（可选，人读）

先写 **核心（相关 + 先后 + 幅度）**，再写 **补充（样本 / 滚动相关）**。不写因果。

---

## 两步产品（逻辑）

| 步 | 做什么 | 产物 |
|----|--------|------|
| 1 计算与呈现 | 拉数 → 并集日历 → 归一化 → `series.json` + `meta.json` | 必有 |
| 2 分析 | 交集上相关 / 简单滞后 → `summary.json` + `findings.md` | `analyze=true` |

CLI 可一次跑完；或 `run` / `analyze` 拆命令（实现期再定）。

---

## 边界

- **不做：** 因子挖掘、策略回测、在 CLI 里画真折线。  
- **复用：** 相关等统计可调 `modules.analysis` 已有原语；拉数走 DataManager / data_contract。  
- **与 analysis 分家：** analysis 解释「一次策略 run」；本模块比较「多条外部/行情曲线」。

---

## 待后续

- BFF / UI 读 `series.json` 画折线（后端完成后再做）。  
- `fill=ffill` 完整实现（需交易/自然日日历）；当前显式 ffill 仍不造点。  
- 示例场景 settings（需真实 data_key/field）。
