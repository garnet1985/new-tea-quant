# Task Guard 设计说明

**版本：** `0.2.0`

| 决策 | 选择 | 理由 |
|------|------|------|
| 入口 | 仅 `TaskGuard` | 统一调用面；直白表达「守卫」而非 pipeline |
| 租约文件 | `userspace/.ntq/runtime/task_guard_active.json` | 与进度等运行时文件同区 |
| 依赖 | 仅 `project_context` | 避免拉起 strategy/tag/db |

## 行为要点

- `lease`：`kind` 须在 `VALID_KINDS`；上下文退出时按 `job_id` 释放
- 忙时 `acquire` 抛 `TaskLeaseBusyError`（携带 `active` 快照）
- 将来若引入真 pipeline/queue：本模块可并入其互斥层，或整体舍弃

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [API.md](../API.md)
