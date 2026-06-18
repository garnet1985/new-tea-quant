# Tag 控制台 BFF：`routes` 编排约定

契约与字段语义以 [`core/ui/fed/src/pages/tagPage/API.md`](../../../fed/src/pages/tagPage/API.md) 为准。

## HTTP 前缀

- 蓝图注册：`url_prefix='/api'`（`core/ui/bff/app.py`）。
- 完整 URL = **`/api`** + 下表路径。

## 目录（待实现）

```
core/ui/bff/APIs/tag/
  __init__.py
  routes.py          # T1-01 … T1-03
  tag_stack.py       # 延迟 import TagManager / launcher
  runtime.py           # job 锁、progress 文件、后台线程
  catalog.py           # list 组装（discovery + last_computed_as_of）
  ROUTES_ORCHESTRATION.md
```

## 原则

- **编排层（routes）**：解析路径/query、调用 catalog / runtime、返回 `ok` / `error`。
- **实现层**：discovery 用 `TagDiscoveryHelper`；执行用 `TagManager.execute(scenario_name=…)`；`last_computed_as_of` 用 `tag_service.get_max_as_of_date`（scenario 下 definition ids）。
- **第 1 层互斥（tag↔tag）**：进程内 tag run 锁 + `_ACTIVE_TAG_JOB_ID`（参考 `scanner_run.py`）。
- **第 2 层互斥（全局 pipeline）**：`core/infra/runtime/pipeline_lease.py` 读写 `userspace/.ntq/runtime/pipeline_active.json`；T1-02 acquire、任务结束 release；T1-00 只读。
- **Progress**：`ProgressRecorder` 风格，`userspace/.ntq/tmp/progress/tag-run/{tag_key}__{job_id}.json`；轮询 **只读**。

## T1 路由 × 编排步骤

| T1 | 方法 | 路由 | 编排摘要 |
|----|------|------|----------|
| T1-00 | GET | `/v1/runtime/pipeline` | `pipeline_lease.read()` → `ok({busy,kind,job_id,...})` |
| T1-01 | GET | `/v1/tags/list` | `pagination_params` → `fetch_discovered_tags_page` → `ok({items,total,page,limit})` |
| T1-02 | POST | `/v1/tag/<path:tag_key>/run` | tag 锁 + `pipeline_lease.acquire(tag_run)` → `trigger_tag_run` → `ok(...)` / **409** |
| T1-03 | GET | `/v1/tag/<path:tag_key>/run/progress` | query `job_id` → `get_tag_run_progress` → `ok` / **404** |

## 错误映射

| 场景 | HTTP | detail 示例 |
|------|------|-------------|
| 未知 `tag_key` | 400 | `未知 Tag scenario: …` |
| `is_enabled=false` | 400 | `Scenario 未启用` |
| 缺少 `job_id` | 400 | `缺少必填 query 参数 job_id` |
| 任务不存在 / tag_key 不匹配 | 404 | `任务不存在或与路径不匹配` |
| 已有 tag run | 409 | `已有 Tag 任务在运行中，请稍后重试` |
| DuckDB 互斥（可选 MVP+） | 409 | `数据库正忙，请稍后再试` |

## 注册

在 `core/ui/bff/app.py` 增加：

```python
from .APIs.tag import tag_api_bp
app.register_blueprint(tag_api_bp, url_prefix="/api")
```

## 测试建议

- BFF 层：`core/ui/bff/APIs/tag/__test__/test_routes_tag_list.py`（mock runtime）
- 列表字段：discovery fixture + 空 tag DB → `last_computed_as_of: null`
