# SeriesRelation（`modules.series_relation`）

**模块：** `modules.series_relation` · **版本：** `0.1.0`

把多条 time series 放到同一时间轴上：日期并集连点呈现，并在交集上给出相关、滞后与缩放关系。

## 适用场景

- 两条指数或宏观序列是否同向、谁领先谁
- 板块内个股是否同形波动，找出滞后的一两只
- 把回测净值与基准并置对照
- 判断一段关系是否稳定（滚动窗口）

## 模块依赖

- `modules.data_source`：序列来源与 `data_key` 声明
- `modules.strategy`：回测产物（组合净值、价格累计）

## 配置与命令

- 配置：`userspace/extensions/series_relation/<key>/settings.py`
- 条数上限：`SeriesRelation.MAX_SERIES`（代码常量）
- CLI：`python cli.py srel KEY` / `series_relation --list`
- 产物：`meta.json` / `series.json` / `summary.json` / `findings.md`

## 相关文档

- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计决策](./docs/DESIGN.md)
