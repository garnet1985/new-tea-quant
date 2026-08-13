# Tag 控制台 BFF：`routes` 编排

**版本：** 0.1.0

契约与字段语义以 [`core/ui/fed/src/pages/tagPage/API.md`](../../../ui/fed/src/pages/tagPage/API.md) 为准。

## HTTP 前缀

- 蓝图注册：`url_prefix='/api'`（`core/bff/app.py`）。
- 完整 URL = **`/api`** + 下表路径。

## 目录

```text
core/bff/APIs/tag/
  api_base.py
  helpers/tag_catalog.py
  routes/
    catalog/     # T1-01
    runner/      # T1-02/03 + tag_run 薄壳
```

进度落盘：``TagRunProgress``（``modules.tag.core.services.progress``）；BFF `tag_run.py` 只做锁 / lease / 线程。

## 原则

- **编排层（routes）**：解析路径/query、调用 implementer、返回 `ok` / `error`。
- **列表**：`helpers.TagCatalog.fetch_page`。
- **执行**：`TagRunLauncher.trigger` → 后台 `Tag().execute`；进度经 `TagRunProgress`。
- **第 1 层互斥（tag↔tag）**：进程内 tag run 锁。
- **第 2 层互斥（全局 pipeline）**：`pipeline_lease`。
- **Progress 文件**：`userspace/.ntq/tmp/progress/tag-run/{tag_key}__{job_id}.json`；轮询只读。

## T1 路由 × 编排步骤

| T1 | 方法 | 路由 | 归属 | 编排摘要 |
|----|------|------|------|----------|
| T1-00 | GET | `/v1/runtime/pipeline` | **platform/runtime**（非本包） | `TaskGuard.read_status()` |
| T1-01 | GET | `/v1/tags/list` | `routes/catalog` | `TagCatalog.fetch_page` |
| T1-02 | POST | `/v1/tag/<path:tag_key>/run` | `routes/runner` | `TagRunLauncher.trigger` → `ok` / **409** |
| T1-03 | GET | `/v1/tag/<path:tag_key>/run/progress` | `routes/runner` | `TagRunProgress.get_poll_dto` → `ok` / **404** |
