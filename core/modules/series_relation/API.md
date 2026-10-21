# SeriesRelation API 文档

**版本：** `0.1.0`  
**最低支持核心版本：** `>=0.5.0`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。

设计见 [docs/DESIGN.md](./docs/DESIGN.md)。术语见 [glossary.yaml](./glossary.yaml)。

**公开约定：** 包根仅导出 `SeriesRelation`；类型从 [`contracts.py`](./contracts.py) 导入。本波无 BFF/UI。

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

### run

`SeriesRelation.run(key_or_id: str) -> dict`

- **状态：** `beta`
- **描述：** 拉数 → 并集日历 → 归一化 → 写入 `results/`（`meta.json` / `series.json` / `summary.json` / `report.txt`；`analyze=true` 时另有 `findings.md`）
- **返回：** `{success, key, output_dir, series_count, calendar_len, report}`；`report` 为 CLI 人读短报告（无图时用白话交代三问，专业指标放括号）
- **分析（`summary.pairwise`）核心三问（白话 + 括号内指标）：**
  1. **同向还是反向**（`norm`）：`relation` / `pearson` / `spearman`
  2. **谁先谁后**（`norm` 滞后相关）：`best_lag_days` / `lead`（`lag>0` ⇒ a 领先 b）
  3. **波动差多少**（`raw` OLS）：`beta_b_on_a` / `alpha_b_on_a` / `scale_r2`
- **门槛：** 交集过短不报；`relation` 为 weak 时 `shape_ok=false`，先后/幅度文案标「请谨慎看待」

**CLI：** `python cli.py series_relation KEY`（缩写 `srel`；`--list` 列场景）

**举例：**

```python
from core.modules.series_relation import SeriesRelation

SeriesRelation.run("cn_index_vs_lpr")  # userspace/extensions/series_relation/cn_index_vs_lpr/
```

---

## contracts

| 符号 | 说明 |
|------|------|
| `DiscoveredRelation` | 已发现场景：`key` / `display_name` / `relative_path` / `folder` / `settings` |
