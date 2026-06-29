# Backtest Scheduler 设计决策

**版本：** `0.1.0`

---

## 决策1: 模块定位

### 问题

调度器应该放在infra层还是modules层？

### 决策

放在modules层（业务调度层）

### 理由

1. **理解业务语义**
   - 理解回测语义（时间线/切片）
   - 不理解通用执行语义
   - 属于业务层，不是基础设施层

2. **职责归属**
   - infra应该提供纯执行能力（ProcessPoolExecutor）
   - modules应该提供业务调度能力
   - 职责清晰，不混淆

3. **Python标准库足够**
   - ProcessPoolExecutor足够好
   - 不需要自定义包装
   - 降低复杂度

---

## 冈策2: 废弃worker模块

### 问题

worker模块是否还需要保留？

### 决策

废弃worker模块（多进程部分）

### 理由

1. **ProcessWorker.run_jobs已废弃**
   - 功能迁移到JobPipeline
   - 不需要自定义包装
   - Python标准库足够

2. **Dispatch规划迁移**
   - resolve_dispatch_plan理解回测语义
   - 应该在backtest_scheduler（modules层）
   - 不属于infra层

3. **类型定义迁移**
   - JobResult/JobStatus是回测结果类型
   - 应该在backtest_scheduler
   - 不属于infra层

---

## 冈策3: 调度逻辑分离

### 问题

backtest_scheduler和data_source scheduler是否应该合并？

### 冈策

不合并，各自独立

### 理由

1. **调度逻辑完全不同**

| 特性 | backtest_scheduler | data_source scheduler |
|------|-------------------|----------------------|
| 执行顺序 | 时间线/切片 | 依赖拓扑排序 |
| 并行策略 | Queue/Batch | bundle并行 |
| 执行池 | ProcessPoolExecutor | ThreadPoolExecutor |
| 特殊逻辑 | Dispatch规划 | retry、依赖注入 |

2. **强行合并导致耦合**
   - scheduler既理解回测语义，又理解数据源语义
   - 职责不清，维护困难

3. **各自优化**
   - backtest：时间线/切片优化
   - data_source：依赖拓扑优化
   - 不互相干扰

---

## 冈策4: Python标准库优先

### 问题

是否需要自定义ProcessExecutor包装？

### 冈策

不需要，直接用ProcessPoolExecutor

### 理由

1. **ProcessPoolExecutor足够好**
   - Python 3.2+标准库
   - 提供submit、shutdown、Future等
   - 不需要重复造轮子

2. **降低复杂度**
   - 不维护自定义包装
   - 减少bug风险
   - 易于理解

3. **调度逻辑在上层**
   - BacktestScheduler负责调度策略
   - ProcessPoolExecutor负责执行
   - 职责清晰

---

## 冈策5: Dispatch规划位置

### 问题

resolve_dispatch_plan应该在哪里？

### 冈策

放在modules.backtest_scheduler

### 理由

1. **理解回测语义**
   - entities_per_job：回测entity数量
   - dispatch_jobs：回测job数量
   - 理解回测业务逻辑

2. **不属于infra**
   - infra应该提供通用基础设施
   - Dispatch规划是业务优化逻辑
   - 应该在modules层

3. **使用模块一致**
   - strategy使用resolve_dispatch_plan
   - tag使用resolve_dispatch_plan
   - 都是回测模块，应该在backtest_scheduler

---

## 冈策6: MQ迁移路径

### 问题

如何设计MQ迁移路径？

### 冈策

不需要抽象接口层，直接替换实现

### 理由

1. **MQ本身有调度能力**
   - RabbitMQ/Kafka提供队列、回调
   - 不需要中间抽象层
   - 减少复杂度

2. **迁移成本低**
   - 业务代码改2行即可
   - 不重构架构
   - 易于实施

3. **符合实际需求**
   - 当前用户：轻量级（ProcessPoolExecutor）
   - 未来用户：MQ分布式
   - 不需要兼容层

---

## 冈策7: QUEUE vs BATCH

### 问题

默认调度策略是什么？

### 冈策

QUEUE是默认，BATCH可选

### 理由

1. **QUEUE优势**
   - 低延迟（完成即补）
   - 高吞吐（持续填池）
   - 适合大多数场景

2. **BATCH适用场景**
   - 内存敏感（峰值控制）
   - checkpoint需求（批间持久化）
   - 特殊优化场景

3. **可配置**
   - worker.json可配置execute_mode
   - 用户可选择
   - 不硬编码

---

## 冈策8: Dispatch规划算法

### 问题

entities_per_job如何计算？

### 冈策

实验优化 + 动态规划

### 理由

1. **实验数据驱动**
   - entities_per_job ∈ [5, 50]
   - 基于真实回测实验（5596股票）
   - 提升20%效率

2. **动态规划**
   - 有measured_mb_per_entity：budget / mb_per_entity
   - 无：启发式规则（5）
   - 自动适应

3. **约束控制**
   - memory_floor_mb保底（1GB）
   - worker_memory_fraction占比（0.85）
   - 内存安全

---

## 冈策9: 模块命名

### 问题

模块叫backtest还是backtest_scheduler？

### 冈策

backtest_scheduler

### 理由

1. **职责明确**
   - scheduler表达调度职责
   - 不是pipeline（更底层）
   - 不是engine（执行）
   - 不是worker（执行者）

2. **不止回测用**
   - 未来可能有其他调度模块
   - scheduler是通用概念
   - backtest_scheduler是特化

3. **命名清晰**
   - 一看就知道是调度器
   - 不混淆

---

## 未来决策（待定）

### 决策10: Timeline Probe + Monitor 分工

**状态**：已采纳（见 [TIMELINE_EXECUTION.md](./TIMELINE_EXECUTION.md)）

**描述**：

- Probe：简单可靠的初值 plan（实验 epj + 内存可行 + workers 上限）
- Monitor：每 N job / M entity 汇总采样，**仅调整 in-flight workers**
- **entities_per_job 全 run 固定**，Monitor 不得修改
- 可选 F（sunk）+ m（margin）在 Monitor 窗口内估算，v1 以内存为主调参

---

### 决策11: Timeline 执行管道

**状态**：已采纳

**描述**：

- 新增 `timeline_based/pipeline/execute_pipeline.py`（`TimelineExecutePipeline`）
- 编排 Planner → Monitor → Executor（进程池 QUEUE 逐步迁入）
- Tag/Strategy 只提交 jobs，不在业务层做 dispatch/plan

---

### 决策12: ELASTIC 模式（原草案）

**状态**：暂缓；由 Monitor 动态 in-flight 覆盖部分目标

---

## 相关文档

- [Timeline 执行规范](./TIMELINE_EXECUTION.md)
- [架构说明](./ARCHITECTURE.md)
- [设计细节](./DESIGN.md)
- [API文档](./API.md)