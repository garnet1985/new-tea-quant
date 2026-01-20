# Worker 重要决策记录

本文档归档 Worker 模块在设计与演进过程中的关键决策，便于后续迭代时参考。

---

## Decision 1：同时保留多进程和多线程两种执行方式

**日期：** 2025-XX-XX  
**状态：** 已实施

### 背景

- 项目中既有大量 **CPU 密集型** 任务（如策略枚举、因子计算），也有大量 **IO 密集型** 任务（如 API 调用、磁盘读写）。
- 单一并发模型（只用线程或只用进程）难以覆盖所有场景。

### 方案

- 提供两类传统 Worker：
  - `ProcessWorker`：基于多进程，适合 CPU 密集型任务
  - `MultiThreadWorker`：基于多线程（Futures），适合 IO 密集型任务
- 在 `TaskType` 中明确标注任务特性，为自动选择策略做准备。

### 理由

1. **性能最优**：CPU 密集任务用多进程绕过 GIL，IO 密集任务用多线程提升吞吐
2. **接口简单**：业务代码可以用统一的 Worker API，而不用自己拼装线程池 / 进程池
3. **向后兼容**：保留已有基于 Worker 的调用方式

---

## Decision 2：引入模块化 Orchestrator，而不是在 Worker 中堆所有功能

**日期：** 2025-XX-XX  
**状态：** 已实施

### 背景

- 早期实现中，Worker 内部集成了：
  - 任务源管理
  - 执行策略
  - 监控与调度
  - 结果聚合
  - 错误处理
- 随着需求增加，单个 Worker 类持续膨胀，难以测试与扩展。

### 方案

- 将 Worker 体系拆分为多个可插拔组件：
  - `Executor` / `JobSource` / `Monitor` / `Scheduler` / `Aggregator` / `ErrorHandler`
  - 使用 `Orchestrator` 将组件组装起来，对外提供 `run()` 接口

### 理由

1. **职责清晰**：每个组件只做一件事（单一职责原则）
2. **易于扩展**：可以为特定场景定制新的 Scheduler / Monitor 等
3. **易于测试**：组件可以单独单元测试
4. **渐进迁移**：传统 Worker 可以在内部逐步迁移到 Orchestrator 实现

---

## Decision 3：采用内存感知调度，而不是固定 batch 大小

**日期：** 2025-XX-XX  
**状态：** 已实施

### 背景

- 固定 batch 大小在不同机器 / 不同任务下表现差异巨大：
  - batch 太大 → OOM 风险高
  - batch 太小 → CPU 利用率不足
- 任务本身的内存占用也可能随数据规模变化。

### 方案

- 使用 `MemoryMonitor` 观察当前进程内存使用情况
- 引入 `MemoryAwareScheduler`：
  - 根据最大内存阈值和历史 batch 行为动态调整下一批任务数量

### 理由

1. **更安全**：在接近内存阈值时自动收缩 batch，降低 OOM 可能性
2. **更高效**：在内存充裕时尽量扩大 batch，提高吞吐
3. **自适应**：无需人为猜测「合适的 batch 大小」，可随任务和环境变化自动调整

---

## Decision 4：使用 TaskType 抽象任务特性，辅助自动选择并发策略

**日期：** 2025-XX-XX  
**状态：** 已实施

### 背景

- 业务方经常问「这个任务到底该用多进程还是多线程？」。
- 不同模块对任务描述不统一，使得 Worker 难以做出合理默认选择。

### 方案

- 定义 `TaskType` 枚举：
  - `CPU_INTENSIVE` / `IO_INTENSIVE` / `MIXED`
- Worker 内部根据 `TaskType` 和 CPU 信息推导合理的 `max_workers`：
  - CPU 密集：接近物理核心数
  - IO 密集：可高于核心数

### 理由

1. **接口清晰**：业务方只需判断任务类型，而不是直接配置复杂的并发参数
2. **可维护性好**：策略调整集中在 Worker 内部，不影响业务代码

---

## Decision 5：保留传统 Worker 接口（ProcessWorker / MultiThreadWorker）

**日期：** 2025-XX-XX  
**状态：** 已实施

### 背景

- 在引入 Orchestrator 之前，已有大量代码依赖 `ProcessWorker` / `MultiThreadWorker`
- 直接强制迁移到 Orchestrator 成本过高

### 方案

- 保留并维护传统 Worker：
  - `ProcessWorker` 用于 CPU 密集批处理
  - `MultiThreadWorker` 用于 IO 密集并发任务
- 在内部逐步重构，使其复用 Orchestrator / Executor 等新组件

### 理由

1. **向后兼容**：避免一次性重写所有调用方
2. **学习曲线平滑**：新老接口并存，业务可按需迁移
3. **风险可控**：可以先在新模块中验证 Orchestrator，再推广到老代码

---

## Decision 6：模块化拆分监控 / 调度 / 聚合 / 错误处理

**日期：** 2025-XX-XX  
**状态：** 已实施

### 背景

- 早期版本中，监控、调度、聚合、错误处理逻辑散落在 Worker 内部和业务代码中
- 无法在不同模块间复用这些通用能力

### 方案

- 创建以下独立子模块：
  - `monitors/`：负责采集指标（从内存开始）
  - `schedulers/`：负责根据指标和配置策略做决策
  - `aggregators/`：负责结果汇总和统计
  - `error_handlers/`：负责错误统一处理策略
- 所有子模块通过统一接口与 Orchestrator 协作

### 理由

1. **解耦**：Worker 本身只关注「执行」，其他关注点被抽离
2. **复用**：监控 / 调度等逻辑可以在不同场景中通用
3. **测试友好**：每个模块可以单独编写测试用例

---

## 相关文档

- 架构设计文档：`architecture/infra/worker/architecture.md`
- 设计细节：`core/infra/worker/DESIGN.md`
- 使用说明：`core/infra/worker/README.md`

