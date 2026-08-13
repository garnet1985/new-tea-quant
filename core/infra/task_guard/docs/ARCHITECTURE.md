# Task Guard 架构文档

**版本：** `0.2.0`

## 模块介绍

`infra.task_guard` 提供与业务编排解耦的**长任务互斥**：忙闲查询与单任务租约。

**核心设计：** Facade `TaskGuard`；实现在 `core/lease`；包 import 不拉起 strategy/tag。

## 职责与边界

**In scope：** 全局长任务 busy 状态、互斥租约 acquire/release  
**Out of scope：** job queue / 多任务调度（将来若有真 pipeline，可 merge 或舍弃本模块）；临时文件清理（`cli.dev.scripts.temp_cleanup`）；从模板新建（`cli.user.scripts.create_from_template`）

## 架构

```text
TaskGuard
  ├── read_status / lease  → core/lease.TaskLease
  └── types                → contracts（含懒加载 TaskLease）
```

## 相关文档

- [DESIGN.md](./DESIGN.md)
- [API.md](../API.md)
