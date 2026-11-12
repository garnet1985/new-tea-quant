# Job Pipeline API 文档

**版本：** `0.1.0`  
**最低支持核心版本：** `>=0.6.0`

> 须与 `module_info.yaml` 的 `version` / `compatible_core_versions` 一致。  
> 只读面已实现（TaskGuard 适配）；`submit` 仍为 planned。设计见 [docs/DESIGN.md](./docs/DESIGN.md)。

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
- **返回值：** ``None`` 或含至少 ``job_id`` / ``kind`` / ``resource_key`` / ``label`` / ``status``（``running``）/ ``domains`` / ``started_at`` / ``progress``（第一期常为 ``None``，细进度由业务侧按 kind 再查）
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
- **描述：** 管道内任务列表。第一期仅含当前 running（0 或 1 条）；pending 队列实现后扩展。
- **返回值：** ``list[dict]``（元素形状同 ``get_running_job``）
- **错误与异常：** 无

### get_job

`JobPipeline.get_job(job_id: str) -> dict | None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 按 id 取单条；第一期仅当 id 等于当前 running 时命中。
- **错误与异常：** 无

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

### advance

`JobPipeline.advance() -> dict | None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 无 running 时弹出队头并交给 handler（launcher ``finally`` 调用）
