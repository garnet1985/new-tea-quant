# Task Guard（`infra.task_guard`）

**模块：** `infra.task_guard` · **版本：** `0.2.0`

长任务互斥租约锁：同时只允许一个全局长任务（Tag / Strategy / renew 等）占用资源。对外门面为 `TaskGuard`。**不是** job queue / 多任务 pipeline 调度；将来若有真 pipeline，本能力可并入或舍弃。

## 适用场景

- BFF / CLI 侧启动长任务前，先拿租约，避免用户连续点击导致两个扫描同时跑
- 长任务中途崩溃后，租约自然过期，后续任务不受阻塞

## 模块依赖

- `infra.project_context`：项目上下文模块：提供常用路径，配置，缓存，项目上下文信息的模块。
## 设计初衷

- **要解决的问题：** 单节点内"同一时刻只允许一个重活"的互斥，靠文件锁实现，跨进程可靠。
- **明确不做：** 不做分布式锁；不做任务重试或恢复；租约过期时间由门面调用方传入。

## 常见问题

**Q：租约文件在哪？**
A：`userspace/system/task_guard/` 下；进程名 + task id 拼唯一文件名。

## 相关文档

- [公开 API](./API.md)
- [架构](./docs/ARCHITECTURE.md)
