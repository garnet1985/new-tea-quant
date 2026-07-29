# Tag 控制台 BFF：`routes` 编排约定

契约与字段语义以 [`core/ui/fed/src/pages/tagPage/API.md`](../../../fed/src/pages/tagPage/API.md) 为准。

## HTTP 前缀

- 蓝图注册：`url_prefix='/api'`（`core/ui/bff/app.py`）。
- 完整 URL = **`/api`** + 下表路径。

## 目录

```text
core/ui/bff/APIs/tag/
  __init__.py
  routes.py
  tag_stack.py              # 延迟 import TagCatalog / TagRunLauncher
  ROUTES_ORCHESTRATION.md
```

实现在 **`core.modules.tag.core.bff_support`**（`TagCatalog` / `TagRunLauncher`），BFF 只做 HTTP 编排。

## 原则

- **编排层（routes）**：解析路径/query、调用 `tag_stack`、返回 `ok` / `error`。
- **实现层**：列表用 `TagCatalog.fetch_page`；执行用 `TagRunLauncher.trigger`（内部 `Tag().execute`）；`last_computed_as_of` 用 `tag_service.get_max_as_of_date`（展示字段，≠ incremental 水位）。
- **第 1 层互斥（tag↔tag）**：进程内 tag run 锁。
- **第 2 层互斥（全局 pipeline）**：`pipeline_lease`（`userspace/.ntq/runtime/pipeline_active.json`）。
- **Progress**：`userspace/.ntq/tmp/progress/tag-run/{tag_key}__{job_id}.json`；轮询只读。

## T1 路由 × 编排步骤

| T1 | 方法 | 路由 | 编排摘要 |
|----|------|------|----------|
| T1-00 | GET | `/v1/runtime/pipeline` | `pipeline_lease.read()` → `ok({busy,...})` |
| T1-01 | GET | `/v1/tags/list` | pagination → `TagCatalog.fetch_page` → `ok({items,total,...})` |
| T1-02 | POST | `/v1/tag/<path:tag_key>/run` | tag 锁 + lease → `TagRunLauncher.trigger` → `ok` / **409** |
| T1-03 | GET | `/v1/tag/<path:tag_key>/run/progress` | `TagRunLauncher.get_progress` → `ok` / **404** |

## 错误映射

| 场景 | HTTP |
|------|------|
| 未知 `tag_key` / 未启用 | 400 |
| 缺少 `job_id` | 400 |
| 任务不存在 / tag_key 不匹配 | 404 |
| 已有 tag run / pipeline busy | 409 |
