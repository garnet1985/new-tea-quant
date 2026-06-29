# Core文件夹结构说明

## 架构层次理解

```text
业务模式层（私有）
├─ timeline_based（时间线模式）
│  ├─ scheduler.py             # entity_timeline调度逻辑
│  ├─ settings.py              # 时间线配置（多进程）
│  ├─ monitor.py               # 监控entity进度
│  └─ strategy/                # QUEUE/BATCH策略
│
└─ slice_based（切片模式）
   ├─ scheduler.py             # slice调度逻辑
   ├─ settings.py              # 切片配置（单进程）
   ├─ orchestrator.py          # Reader ∥ Compute编排
   ├─ monitor.py               # 监控切片进度
   └─ strategy/                # parallel/preload策略

共用基础组件层（shared）
├─ job_pipeline.py             # JobPipeline核心（queue/batch框架）
├─ dispatch_planner.py         # Dispatch规划（通用）
├─ dispatch_time_planner.py    # 时间规划（通用）
├─ types.py                    # 类型定义（通用）
└─ utils.py                    # 工具函数（如果有）
```

---

## 为什么这样设计？

### 业务模式层（私有）

**timeline_based私有逻辑**：
- scheduler：entity_timeline调度（逐entity、逐交易日）
- settings：多进程配置（max_workers、execute_mode）
- monitor：监控entity进度（已完成多少entity）
- strategy：基于JobPipeline的QUEUE/BATCH策略

**slice_based私有逻辑**：
- scheduler：slice调度（按日期切片批量执行）
- settings：单进程配置（max_workers=1）
- orchestrator：内部编排器（Reader ∥ Compute）
- monitor：监控切片进度（已完成多少切片）
- strategy：parallel/preload策略（Reader ∥ Compute）

---

### 共用基础组件层（shared）

**真正共用的组件**：
- job_pipeline.py：JobPipeline核心（queue/batch框架），两种模式都用
- dispatch_planner.py：Dispatch规划（resolve_dispatch_plan、resolve_memory_budget_mb）
- dispatch_time_planner.py：时间规划（resolve_time_dispatch_plan）
- types.py：类型定义（JobResult、JobStatus等），两种模式都用

---

## 模式对比

| 特性 | timeline_based | slice_based |
|------|---------------|-------------|
| 调度逻辑 | entity_timeline（逐entity） | slice（按日期切片） |
| Settings | 多进程（max_workers=N） | 单进程（max_workers=1） |
| Monitor | entity进度监控 | 切片进度监控 |
| 内部编排 | 无（直接JobPipeline） | Reader ∥ Compute |
| 适用模块 | Tag | Strategy |

---

## 调用关系

```text
timeline_based/scheduler
    ↓ 调用
shared/job_pipeline（queue/batch框架）
    ↓ 调用
shared/dispatch_planner（Dispatch规划）

slice_based/scheduler
    ↓ 调用
shared/job_pipeline（queue/batch框架）
    ↓ 调用
shared/dispatch_planner（内存预算）
slice_based/orchestrator（内部编排）
```

---

## 关键设计原则

### 1. 业务模式私有

- 每种模式有自己的scheduler（调度逻辑不同）
- 每种模式有自己的settings（配置不同）
- 每种模式有自己的monitor（监控对象不同）

### 2. 基础组件共用

- JobPipeline是通用调度框架（两种模式都用）
- dispatch_planner提供基础规划函数（两种模式都用）
- types提供基础类型定义（两种模式都用）

### 3. 调用关系清晰

- 业务模式层调用共用基础组件层
- 不反向调用（shared不调用timeline_based/slice_based）

---

## 下一步实施

**Phase 2: 迁移shared基础组件**
- job_pipeline.py（从infra.job_pipeline迁移）
- dispatch_planner.py（从infra.worker迁移）
- dispatch_time_planner.py（从infra.worker迁移）
- types.py（从infra.worker迁移）

**Phase 3: 实现业务模式层**
- timeline_based/scheduler.py
- slice_based/scheduler.py
- timeline_based/settings.py
- slice_based/settings.py
- timeline_based/monitor.py
- slice_based/monitor.py

**Phase 4: 完善策略和编排**
- timeline_based/strategy/
- slice_based/strategy/
- slice_based/orchestrator.py

---

## 相关文档

- [架构说明](../docs/ARCHITECTURE.md)
- [设计细节](../docs/DESIGN.md)
- [设计决策](../docs/DECISIONS.md)