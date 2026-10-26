# SeriesRelation（`modules.series_relation`）

**模块：** `modules.series_relation` · **版本：** `0.1.0`

把多条 time series 放到同一时间轴上：日期并集连点呈现，并在交集上给出相关、滞后与缩放关系。

## 适用场景

- 两条指数或宏观序列是否同向、谁领先谁
- 板块内个股是否同形波动，找出滞后的一两只
- 把回测净值与基准并置对照
- 判断一段关系是否稳定（滚动窗口）

## 模块依赖

- `infra.discovery`
- `infra.project_context`
- `modules.data_contract`：数据契约模块：提供一套可扩展的数据声明到数据加载的契约，主要目的是为了实现回测过程中的声明式数据注入
- `modules.data_manager`：数据管理模块：提供统一的数据访问门面，支持对不同数据源的访问和查询。
- `modules.strategy`：策略执行模块：Strategy facade 提供 scan / simulate / discov
## 常见问题

**Q：配置和产物在哪？**  
A：配置 `userspace/extensions/series_relation/<key>/settings.py`；产物 `meta.json` / `series.json` / `summary.json` / `findings.md`；条数上限 `SeriesRelation.MAX_SERIES`（代码常量）。CLI：`python cli.py srel KEY`。

## 相关文档

- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计决策](./docs/DESIGN.md)
