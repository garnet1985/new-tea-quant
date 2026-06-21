# Data Source 控制台 UI — 决策记录（Phase 2）

更新时间：2026-06-18

## 范围

在 Tag MVP 完成后实施。原型参考 `prototype/data-acquire.html` 的 **Data Source** Tab（不含 Data Contract / Tables）。

| 包含（Phase 2 MVP） | 不包含 |
|---------------------|--------|
| Source 列表（只读） | 编辑 `mapping.py` / handler `config.py` |
| 单行 Renew + 可选「Renew 全部」 | Data Contract 调试、Tables CRUD |
| 进度展示 | Dry-run 独立模式（若 CLI 仅 `is_dry_run` 配置则不做 UI 切换） |

## 路由

| 路径 | 说明 |
|------|------|
| `/data-sources` | 列表 + Renew |

主导航可在 Phase 2 增加「数据」入口；无 `/advanced` landing。

## 后端

- 列表：`DataSourceManager.list_renew_targets()` + mapping 元数据扩展。
- 执行：`DataSourceManager.renew(table_name=source_key)` / 全量 renew。
- 并发：与 Tag / Strategy 共享 DuckDB 约束；renew 写 `data.duckdb`，运行中应 **409** 或 disable。

契约见 [`API.md`](./API.md)（T2-xx）。
