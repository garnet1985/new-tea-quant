# Job Pipeline — 架构

**版本：** `0.1.0`

目标结构（实现后）。现状仅为门面骨架，见 [DESIGN.md](./DESIGN.md)。

---

## 逻辑视图

```text
调用方（BFF launcher / 将来 CLI）
        │
        ▼
   JobPipeline（门面）
        │
        ├── Registry（任务表：id → 快照）
        ├── Queue / Scheduler（pending → running；第一期全局串行）
        ├── Progress view（阶段 / ratio；内部可嵌进度树）
        └── Liveness（pid / 心跳 → 纠正 stale；互斥换心后优先 filelock）
```

绞杀期：Scheduler / Liveness 可暂时委托 `TaskGuard`；进度委托 `Progress` / 各业务 Progress 包装。  
换心期：跨进程互斥优先 `filelock.FileLock`（见 DECISIONS DEC-06），任务表仍由本模块自管。

---

## 部署与存储（预期）

- 任务表与租约类元数据：落在 `userspace/.ntq/runtime/`（具体文件名实现时定）
- 不引入新的业务 DB；单机文件 + 进程内调度即可

---

## 相关文档

- [设计结论](./DESIGN.md)
- [决策](./DECISIONS.md)
