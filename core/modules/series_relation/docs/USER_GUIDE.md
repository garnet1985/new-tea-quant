# SeriesRelation — 用户指南

**版本：** `0.1.0`

`SeriesRelation 把多条时间序列放一起看——算相关性、找滞后、对比形态。`  
相关：[README.md](../README.md) · [API.md](../API.md) · [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 功能总览

- 把 2～6 条时间序列放在同一时间轴上对齐（K 线、宏观指标、回测净值都行）
- 算两两相关强度和方向（Pearson / Spearman）
- 找滞后天数：谁领先谁几天
- 算缩放比例：一条序列大致是另一条的几倍（β / α）
- 看滚动稳定性：这个关系是不是最近还在

## 配置说明

在 `userspace/extensions/series_relation/<你的key>/settings.py` 里写：

| 配项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `meta.key` / `meta.display_name` | 字符串 | 必填 | 这次对比的标识和显示名 |
| `series` | 列表 | 必填 | 要对比的序列，最多 6 条；每条指明 `data_key` + `field`（可带 `entity_id`、`label`），或指策略回测产物 |
| `range.start_date` / `range.end_date` | 字符串 | 空 | 限定时间窗口；留空用全部可得数据 |
| `normalize` | 字符串 | `zscore` | 归一化方式；也可选起点归一 |
| `fill` | 字符串 | `none` | 缺口补齐方式 |
| `analyze` | 布尔 | `True` | 是否生成两两指标和文字结论 |
| `transform` | 字符串 | 视来源 | 对每条序列可单独设：`none` / `returns` / `diff` |

`max_series` 是模块代码常量（=6），不能配置。

## 常见使用方式

### 场景 1：对比大盘指数与宏观指标（例：沪深300 vs LPR）

1. 确认本地已有 `index.kline.daily`（000300.SH）和 `macro.lpr` 数据。
2. 在 `userspace/extensions/series_relation/cn_index_vs_lpr/settings.py` 里列两条序列：一条 `data_key=index.kline.daily, entity_id=000300.SH, field=close`，一条 `data_key=macro.lpr, field=lpr_1_y`。
3. 跑 `python cli.py srel cn_index_vs_lpr`。
4. 终端看核心结论，详细结果落在 `results/` 下的 `summary.json` 和 `findings.md`。

### 场景 2：比较板块内多只股票

1. 在 `series` 里列多只股票（同一 `data_key`，不同 `entity_id`）。
2. 设置相同的时间窗口和归一化方式。
3. 跑批后看两两相关矩阵——大多数高度相关说明板块整体联动，个别落后的可能就是洼地或风险点。

### 场景 3：对比策略净值与基准

1. 序列 1 指策略回测产物：`strategy_key=<策略key>, layer=portfolio, metric=equity`（版本默认 `latest`）。
2. 序列 2 指基准指数：如沪深 300 收盘价。
3. 跑批后看 β / α：β 接近 1 说明和大盘同涨跌，α 才是策略真正的超额。

### 场景 4：用 CLI 查看已有结果

1. `python cli.py srel` 列出所有已定义的对比。
2. `python cli.py srel <key>` 重新跑某个对比。
3. 结果文件在 `userspace/extensions/series_relation/<key>/results/`，包含 `report.txt`、`summary.json`、`findings.md`、`series.json`、`meta.json`。

## 常见坑与注意事项

- **想放第 7 条序列会报错**：上限是 6 条（`MAX_SERIES`）。先合并或分批。
- **滞后结论别当交易信号**：模块只在归一化水平值上扫 ±20 天找最相关点，水平值自相关强、对噪声敏感，"领先/落后 N 天"只能当参考。
- **重叠样本太少时指标不可信**：序列重叠不足会标 `reliable=False`，这种时候的相关、β 都别拿来下结论。
- **相关 ≠ 因果**：模块只描述统计关系，不做因果推断、不做预测、不给你买卖建议。
- **`portfolio.equity` 不能加 `entity_id`**：组合净值是整体的，单票要用 `layer=price, metric=cum_exit_roi`。

## 相关文档

- [概览 README](../README.md)
- [公开 API](../API.md)
- [架构](./ARCHITECTURE.md)
- [术语表](../glossary.yaml)
