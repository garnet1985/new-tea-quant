# NTQ Prototype 页面文档索引

用于 React Prototype 与 API 设计前的页面语义对齐。每个页面对应一个独立文档，统一包含：
- 页面是什么
- 页面目的/用户价值
- 功能描述
- 假设与 placeholder

## 页面文档清单
- `DOC_workbench.md` -> `workbench.html`
- `DOC_workbench-detail.md` -> `workbench-detail.html`
- `DOC_workbench-stock.md` -> `workbench-stock.html`
- `DOC_scan.md` -> `scan.html`
- `DOC_setup.md` -> `setup.html`
- `DOC_data-acquire.md` -> `data-acquire.html`
- `DOC_tag-console.md` -> `tag-console.html`
- `DOC_tag-preview.md` -> `tag-preview.html`
- `DOC_backup-and-restore.md` -> `backup-and-restore.html`
- `DOC_settings.md` -> `settings.html`
- `DOC_backtest.md` -> `backtest.html`
- `DOC_run-center.md` -> `run-center.html`

## React 实现契约（已落地）

| 页面 | 决策 | API |
|------|------|-----|
| Tag 列表 / 运行 | `fed/src/pages/tagPage/DECISIONS.md` | `fed/src/pages/tagPage/API.md`（T1-xx） |
| Data Source（Phase 2） | `fed/src/pages/dataSourcePage/DECISIONS.md` | `fed/src/pages/dataSourcePage/API.md`（T2 草案） |
| BFF 编排 | — | `bff/APIs/tag/ROUTES_ORCHESTRATION.md` |

## 建议交接方式
- React：按 `tagPage/DECISIONS.md` 路由 `/tags` + 列表 DataGrid，运行对齐 scan 页轮询。
- BFF：按 `tagPage/API.md` T1-01～03 与 `ROUTES_ORCHESTRATION.md` 实现。
- 对“非主流程页”（如 `tag-preview`、`run-center`、`backtest`）仍低优先级。
