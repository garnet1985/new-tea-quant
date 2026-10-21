# series_relation

多条 time series 曲线并置：日期并集连点呈现，可选交集上的关系摘要。

**状态：** `0.1.0` 后端可用；**无 BFF/UI**。约定见 [docs/DESIGN.md](./docs/DESIGN.md)、[API.md](./API.md)。

**用户配置：** `userspace/extensions/series_relation/<key>/settings.py`  
**条数上限：** `SeriesRelation.MAX_SERIES`（代码常量）  
**CLI：** `python cli.py srel KEY` / `series_relation --list`
