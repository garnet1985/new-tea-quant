# Job Pipeline API 文档

**版本：** `0.1.0`  
**最低支持核心版本：** `>=0.6.0`

> 须与 `module_info.yaml` 的 `version` / `compatible_core_versions` 一致。  
> 只读任务表 + 串行队列 + `submit` / `running_lease`（filelock 自管槽）已落地。业务 launcher 公开入口统一 `JobPipeline.submit`；handler 调 `start_now`；互斥用 `running_lease`。设计见 [docs/DECISIONS.md](./docs/DECISIONS.md)。

**公开约定：** 包根仅导出 `JobPipeline`；状态常量见 [`contracts.py`](./contracts.py)。

---

## JobPipeline

**描述：** 长任务登记 / 排队 / 只读视图门面

### get_running_job

`JobPipeline.get_running_job() -> dict | None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 返回当前 running 任务快照；没有长任务在跑时返回 ``None``。串行期 BFF/FED 主读面。
- **返回值：** ``None`` 或含至少 ``job_id`` / ``kind`` / ``resource_key`` / ``label`` / ``status``（``running``）/ ``domains`` / ``started_at`` / ``cancel_requested`` / ``progress``（有则挂 ``infra.progress`` 摘要：``ratio`` / ``percent`` / ``label`` / ``detail``；细进度仍可直接读 Progress）
- **错误与异常：** 无

### has_running_job

`JobPipeline.has_running_job() -> bool`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** ``get_running_job() is not None``
- **返回值：** ``bool``
- **错误与异常：** 无

### list_jobs

`JobPipeline.list_jobs() -> list[dict]`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 管道内活跃任务：当前 running（0 或 1 条）+ pending 队列（按入队顺序）。
- **返回值：** ``list[dict]``（running 形状同 ``get_running_job``；pending 含 ``status=pending``，``progress`` 常为 ``None``）
- **错误与异常：** 无

### get_job

`JobPipeline.get_job(job_id: str) -> dict | None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 按 id 取单条；命中当前 running 或 pending 队列中的项。
- **错误与异常：** 无

### running_lease

`JobPipeline.running_lease(*, kind, job_id, resource_key="", label="", domains=None) -> RunningLease`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 占用全局 running 槽（`filelock` + 自管表）。忙则 ``JobRunningBusyError``。
- **返回值：** 含 ``acquire`` / ``release`` 的租约对象

### enqueue

`JobPipeline.enqueue(spec: dict) -> dict`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 只入 pending 队列（有上限；同 kind+resource 去重）
- **返回值：** 成功含 ``queued=True`` / ``job_id``；失败 ``queued=False`` + ``reason``

### submit

`JobPipeline.submit(spec: dict) -> dict`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 空闲则调已注册 handler 开跑；忙则 ``enqueue``。handler 由 BFF 启动时 ``register_handler`` 注入。

### cancel

`JobPipeline.cancel(job_id: str) -> dict`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 删除尚未执行的 pending；若 ``job_id`` 是当前 running，则写入 ``cancel_requested``（协作取消，后台需轮询 ``is_cancel_requested``）。
- **返回值：** 成功 ``cancelled=True``（running 时另有 ``cancel_requested=True``）；失败 ``cancelled=False`` + ``reason``

### is_cancel_requested

`JobPipeline.is_cancel_requested(job_id: str) -> bool`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 后台线程查询用户是否已请求取消该 running。

### advance

`JobPipeline.advance() -> dict | None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 无 running 时弹出队头并交给 handler。一般经 ``notify_job_finished`` 间接调用。

### notify_job_finished

`JobPipeline.notify_job_finished() -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** launcher ``finally`` 调用：尝试 ``advance`` 泵下一条；失败只打日志。

### recover

`JobPipeline.recover() -> dict`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 若 running 槽 pid 已死则清槽并 ``advance``。BFF 读面轮询时调用。
- **返回值：** ``recovered``；为真时含 ``reason=dead_pid`` / ``cleared_job_id``

### abandon

`JobPipeline.abandon(job_id: str) -> dict`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 强制释放当前 running（僵死任务），写 Progress.fail，并泵下一条。产品 UI 仅在 ``status=stale`` 时暴露。
- **返回值：** 成功 ``abandoned=True``；失败 ``abandoned=False`` + ``reason``

### register_handler

`JobPipeline.register_handler(kind: str, handler) -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** BFF 启动时注册 ``kind → start_now`` 回调；``submit`` / ``advance`` 依赖此表。
