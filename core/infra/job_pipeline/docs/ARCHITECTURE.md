# Job Pipeline — 架构

**版本：** `0.1.0`

逻辑结构见下文。阶段完成情况见 [DESIGN.md](./DESIGN.md) §5。

---

## 逻辑视图

```text
调用方（BFF launcher / 将来 CLI）
        │
        ▼
   JobPipeline（门面）
        │
        ├── Registry（任务表：id → 快照；running 槽落盘）
        ├── Queue / Scheduler（pending → running；第一期全局串行）
        ├── Progress view（阶段 / ratio；内部可读 Progress 树）
        └── Liveness（pid 存活检查 → 纠正 stale；跨进程互斥用 filelock）
```

**现状：** running 槽与队列由本模块自管（`filelock`）。细进度由 `infra.progress` 提供，任务表可挂摘要。

---

## 部署与存储

- 任务表 / 队列 / running 槽：`userspace/.ntq/runtime/`
  - `job_pipeline_running.json`（+ `.lock`）
  - `job_pipeline_queue.json`（+ `.lock`）
- 进度树文件仍由 `infra.progress` 管理（不并入本目录协议）
- 不引入新的业务 DB；单机文件 + 进程内调度即可

---

## 相关文档

- [设计结论](./DESIGN.md)
- [决策](./DECISIONS.md)
