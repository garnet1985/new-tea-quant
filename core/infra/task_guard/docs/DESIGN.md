# Task Guard 设计说明

**版本：** `0.2.0`

关键选型见 [DECISIONS.md](./DECISIONS.md)：DEC-01（单一入口）、DEC-02（租约文件位置）、DEC-03（仅依赖 project_context）、DEC-04（文件锁而非内存锁）、DEC-05（将来可并入 pipeline）。

## 行为要点

- `lease`：`kind` 须在 `VALID_KINDS`；上下文退出时按 `job_id` 释放
- 忙时 `acquire` 抛 `TaskLeaseBusyError`（携带 `active` 快照）
- 将来若引入真 pipeline/queue：本模块可并入其互斥层，或整体舍弃

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [API.md](../API.md)
