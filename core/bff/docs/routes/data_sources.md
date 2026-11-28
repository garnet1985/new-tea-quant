# Data sources BFF

**模块：** `bff` · **版本：** `0.2.2`

**最低支持核心版本：** `>=0.5.0`

契约见 [`core/ui/fed/src/pages/dataSourcePage/API.md`](../../../ui/fed/src/pages/dataSourcePage/API.md)（有则）。

## 目录

```text
core/bff/APIs/data/sources/
  routes.py
  implementer.py
  helpers/source_catalog.py
```

## 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/v1/data-sources/list` | 分页数据源目录（静态字段） |
| GET | `/v1/data-sources/freshness` | 懒加载 freshness vs data.json |
