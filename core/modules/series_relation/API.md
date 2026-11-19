# SeriesRelation API 文档

**版本：** `0.1.0`  
**最低支持核心版本：** `>=0.5.0`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。

设计与决策见 [docs/DECISIONS.md](./docs/DECISIONS.md)。术语见 [glossary.yaml](./glossary.yaml)。

**公开约定：** 包根仅导出 `SeriesRelation`；类型从 [`contracts.py`](./contracts.py) 导入。CLI、BFF 与 UI 均只经本 Facade。

---

## SeriesRelation

**描述：** 多条 time series 并置比较（发现 / 校验 / 跑批落盘）

- **状态：** `beta`
- **引入版本：** `0.1.0`

### MAX_SERIES

`SeriesRelation.MAX_SERIES -> int`

- **状态：** `beta`
- **描述：** 单次比较条数上限（代码常量，默认 6；不进用户 settings）

### list_infos / list_keys / find

`SeriesRelation.list_infos() -> list[DiscoveredRelation]`  
`SeriesRelation.list_keys() -> list[str]`  
`SeriesRelation.find(key_or_id: str) -> DiscoveredRelation | None`

- **状态：** `beta`
- **描述：** 扫描 `userspace/extensions/series_relation/**/settings.py`

### validate

`SeriesRelation.validate(settings: Mapping) -> dict`

- **状态：** `beta`
- **描述：** 返回 `{ok, settings, errors}`；规范化后的 settings 不含 `max_series`

### scaffold_user_series_relation / write_user_series_relation_settings / validate_user_series_relation / describe_user_series_relation / list_user_series_relation_summaries

`SeriesRelation.scaffold_user_series_relation(*, key, display_name="") -> dict`（staticmethod）  
`SeriesRelation.write_user_series_relation_settings(*, key, settings_py="") -> dict`（staticmethod）  
`SeriesRelation.validate_user_series_relation(*, key) -> dict`（staticmethod）  
`SeriesRelation.describe_user_series_relation(*, key) -> dict`（staticmethod）  
`SeriesRelation.list_user_series_relation_summaries() -> dict`（staticmethod）

- **状态：** `beta`
- **描述：** Userspace 场景脚手架与按 key 校验（实现在 `user_relations`）。从 `_template/empty_relation` 复制；发现即注册，无 mapping。`meta.key` 与目录叶名对齐。

### save

`SeriesRelation.save(key_or_id: str, settings: Mapping) -> dict`

- **状态：** `beta`
- **描述：** 校验后写入 `userspace/extensions/series_relation/<key>/settings.py`（`meta.key` 强制对齐路径）；目录不存在则创建
- **返回：** `{success, key, settings, ...}`；失败含 `errors` / `error`

### run

`SeriesRelation.run(key_or_id: str) -> dict`

- **状态：** `beta`
- **描述：** 拉数 → 可选 `transform` → 并集日历 → 归一化 → 写入 `results/`（`meta.json` / `series.json` / `summary.json` / `report.txt`；`analyze=true` 时另有 `findings.md`）
- **返回：** `{success, key, output_dir, series_count, calendar_len, report}`；失败时 `{success: false, error}`（装载硬失败，如缺回测层）
- **序列源（`series[]` 每项）：**
  - **契约**：`data_key` + `field`（[+ `entity_id`]）；默认 `transform=none`
  - **回测**：`source: "strategy_sim"` + `strategy_key`（推荐 `meta.key`；也可用相对路径；别名 `strategy`）+ `layer` + `metric`；`version` 默认 `latest`；默认 `transform=returns`
    - Phase1 metric：`portfolio.equity`（`equity_curve.json`）；`price.cum_exit_roi`（按平仓日累加已实现 ROI，可选 `entity_id` 单票）
    - `portfolio.equity` 禁止 `entity_id`；缺层/空点硬失败，不静默换更旧 version
- **分析（`summary.pairwise`）核心三问（白话 + 括号内指标）：**
  1. **同向还是反向**（`norm`）：`relation` / `pearson` / `spearman`
  2. **谁先谁后**（`norm` 滞后相关）：`best_lag_days` / `lead`（`lag>0` ⇒ a 领先 b）
  3. **波动差多少**（`raw` OLS）：`beta_b_on_a` / `alpha_b_on_a` / `scale_r2`
- **门槛：** 交集过短不报；`relation` 为 weak 时 `shape_ok=false`，先后/幅度文案标「请谨慎看待」

### load_results

`SeriesRelation.load_results(key_or_id: str, *, max_points: int = 800) -> dict`

- **状态：** `beta`
- **描述：** 读 `results/`（meta / summary / 抽稀 chart / report 文本）供 UI

**CLI：** `python cli.py series_relation KEY`（缩写 `srel`；`--list` 列场景）

**BFF：** `/api/v1/series-relations/*`（list / get / put / run / results）→ 只调本 Facade

**举例：**

```python
from core.modules.series_relation import SeriesRelation

SeriesRelation.run("cn_index_vs_lpr")
SeriesRelation.run("demo_portfolio_vs_hs300")  # strategy_sim 组合权益 vs 指数
```

---

## contracts

| 符号 | 说明 |
|------|------|
| `DiscoveredRelation` | 已发现场景：`key` / `display_name` / `relative_path` / `folder` / `settings` |
