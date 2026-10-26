# Task Guard — 决定

**版本：** `0.2.0`

本文列出长任务互斥锁模块的关键选型回顾。  
相关：[ARCHITECTURE.md](./ARCHITECTURE.md) · [DESIGN.md](./DESIGN.md)

---

## DEC-01：单一入口 TaskGuard

**是什么：** 包根只导出 `TaskGuard` 门面，作为唯一调用面。

**为什么选它：**

- 统一调用面，直白表达"守卫"语义而非 pipeline
- 防止内部 Lease / LockFile 等实现细节泄漏到调用方

**放弃了什么：**

- **函数式 API：** 顶层 `acquire()` / `release()` — 失去上下文管理器语义，调用方易忘 release

---

## DEC-02：租约文件放在 userspace/.ntq/runtime/

**是什么：** 租约文件路径为 `userspace/.ntq/runtime/task_guard_active.json`，与进度等运行时文件同区。

**为什么选它：**

- 运行时状态集中存放，便于清理与排查
- 与 `infra.progress` 的进度文件同目录结构，心智一致
- userspace 隔离——多项目并存时互不干扰

**放弃了什么：**

- **放在 core 目录：** 跨项目共享租约 — 不同项目的任务会互相阻塞，不符合隔离语义
- **/tmp 目录：** 系统重启即清理 — 崩溃后无法区分"任务还在跑"与"系统重启"

---

## DEC-03：仅依赖 project_context

**是什么：** 模块只 import `infra.project_context`，不依赖 strategy / tag / db。

**为什么选它：**

- 保持基础设施层纯净，避免拉起业务模块
- 依赖链最短，启动开销最小

**放弃了什么：**

- **依赖 db 记录租约：** 用数据库行锁替代文件锁 — 引入 db 启动开销，且 db 本身可能被 guard 保护的任务占用

---

## DEC-04：用文件锁而非内存锁

**是什么：** 跨进程互斥通过文件系统实现，不依赖 threading.Lock 或 multiprocessing.Lock。

**为什么选它：**

- 多进程环境下内存锁无效——CLI、BFF、Agent 可能各自起进程
- 文件锁天然跨进程可见
- 租约带过期时间，崩溃后自动释放

**放弃了什么：**

- **内存锁：** 实现简单 — 仅限单进程，CLI 与 UI 同时跑时失效
- **系统级 flock：** 平台差异大（Windows 无 flock） — 跨平台兼容性差

---

## DEC-05：将来若引入真 pipeline 可并入或舍弃

**是什么：** 本模块定位为"单机互斥锁"，不做任务队列或流水线调度；将来若引入真 pipeline/queue，本模块可并入其互斥层，或整体舍弃。

**为什么选它：**

- 当前需求仅是"同一时刻一个重活"，不需要完整队列
- 预留演进空间，避免过度设计

**放弃了什么：**

- **直接实现任务队列：** 支持排队、优先级、重试 — 当前无此需求，过度设计

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [设计思路](./DESIGN.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
