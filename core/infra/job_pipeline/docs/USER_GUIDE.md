# Job Pipeline — 用户指南

**版本：** `0.1.0`

## 调用方（BFF launcher）

1. 校验参数后只调 `JobPipeline.submit(spec)`，不要直接抢跑。
2. 真正开跑写在 `start_now`；由 `register_handler(kind, …)` 接到管道。
3. `start_now` 内用 `JobPipeline.running_lease(...)` 占槽；忙则抛 `JobRunningBusyError`（通常不应发生：公开入口已走 submit）。
4. 循环里轮询 `JobPipeline.is_cancel_requested(job_id)`；用户取消时协作退出。
5. `finally` 调 `JobPipeline.notify_job_finished()`，泵下一条 pending。

## 读面（BFF / FED）

- `GET /api/v1/runtime/pipeline` → `get_running_job` / `list_jobs`
- 取消 → `JobPipeline.cancel(job_id)`（pending 直接删；running 写 `cancel_requested`）
- 细进度仍用 `infra.progress`；任务表上的 `progress` 只是摘要

## 产品 UI

左下角管道坞：活跃任务 + 前端「未读完成」缓冲；可取消 pending / 请求取消 running；完成行「查看」后消掉。不保留真历史。

更多产品约定见 [DESIGN.md](./DESIGN.md)。
