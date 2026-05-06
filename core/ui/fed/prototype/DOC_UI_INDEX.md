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

## 建议明天交接方式
- React agent 先按页面文档拆 component 边界与路由。
- API 设计 agent 按“功能描述 vs placeholder”逐页列接口草案。
- 对“非主流程页”（如 `tag-preview`、`run-center`、`backtest`）先做低优先级处理。
