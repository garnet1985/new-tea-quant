# Post-process 路由

编排见 `core/bff/APIs/post_process/`。FED 契约：`core/ui/fed/src/pages/postProcessPage/API.md`。

| 方法 | 路径 | 实现 |
|------|------|------|
| GET | `/v1/post-process/adapters` | `PostProcess.list_adapter_summaries` |
| GET | `/v1/post-process/processors` | `PostProcess.list_post_processor_summaries` |
| POST | `/v1/post-process/processors/<key>/enabled` | `PostProcess.set_enabled` |
| PUT | `/v1/post-process/processors/<key>/adapters` | `PostProcess.update_post_processor_adapters` |

分层：`routes.py` → `implementer` → `helpers/catalog.py` → Facade。
