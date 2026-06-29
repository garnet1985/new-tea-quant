# 最终架构决策

**日期**：2026-06-28

---

## 核心决策

### 1. 废除worker模块 ✅

**理由**：
- ProcessWorker.run_jobs已废弃（多进程执行移到JobPipeline）
- MultiThreadWorker没人用（DataSource直接用JobPipeline）
- Dispatch规划应该在backtest_scheduler（理解回测语义）
- Python标准库足够（ProcessPoolExecutor/ThreadPoolExecutor）

**迁移计划**：
```
infra.worker → 完全废弃
├─ dispatch_planner.py → modules.backtest_scheduler
├─ dispatch_time_planner.py → modules.backtest_scheduler
├─ process_worker.py
│  ├─ JobResult → modules.backtest_scheduler.types
│  ├─ JobStatus → modules.backtest_scheduler.types
│  └─ ProcessWorker → 删除
└─ Worker Facade → 删除
```

---

### 2. modules.backtest_scheduler ✅

**定位**：
- tag/strategy共用的回测调度模块
- 理解回测语义（时间线/切片）
- 不属于infra层（业务调度层）

**职责**：
```text
modules.backtest_scheduler/
├─ scheduler.py          # 调度器核心（从job_pipeline迁移）
├─ dispatch_planner.py   # Dispatch规划（从worker迁移）
├─ dispatch_time_planner.py # 时间规划（从worker迁移）
├─ types.py              # JobResult/JobStatus（从worker迁移）
├─ strategy/             # 调度策略
│  ├─ queue_strategy.py
│  └─ batch_strategy.py
└─ module_info.yaml
```

**核心功能**：
- 队列填池策略（QUEUE/BATCH）
- on_result回调机制
- JobContext封装
- Dispatch规划（entities_per_job、max_workers）

---

### 3. data_source内置scheduler ✅

**定位**：
- data_source专属调度器
- 不共享给其他模块
- 理解数据源语义（依赖关系）

**理由**：
- **调度逻辑完全不同**（拓扑排序 vs 时间线切片）
- **避免过度耦合**（强行合并会职责不清）
- **独立优化**（retry、依赖注入）

**架构**：
```text
modules.data_source/
├─ execution_scheduler.py     # 串行调度（拓扑排序）
├─ service/
│  └─ pipeline/
│     └─ runner.py            # 并行调度（bundle抓取）
│        # 直接用ThreadPoolExecutor（废弃job_pipeline后）
└─ （不依赖外部scheduler）
```

**废弃job_pipeline后的实现**：
```python
class DataSourcePipelineRunner:
    def run_bundles(self, bundles):
        # 直接用Python标准库
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = [pool.submit(self._run_bundle, b) for b in bundles]
            for future in as_completed(futures):
                result = future.result()
                self.on_result(result)
```

---

## 最终架构（三层）

```text
┌─────────────────────────────────────┐
│ modules（业务层）                     │
│ ├─ backtest_scheduler（共用）         │
│ │  ├─ tag/strategy共用                │
│ │  ├─ 回测调度逻辑                    │
│ │  └─ Queue/Batch策略                │
│ │                                    │
│ ├─ data_source（内置scheduler）       │
│ │  ├─ execution_scheduler.py         │
│ │  ├─ pipeline/runner.py             │
│ │  ├─ 拓扑排序、依赖注入              │
│ │  └─ bundle并行抓取                 │
│ │                                    │
│ ├─ tag                               │
│ ├─ strategy                          │
└─ （其他业务模块）                      │
└─────────────────────────────────────┘
         ↓ 调用
┌─────────────────────────────────────┐
│ Python标准库（执行层）                 │
│ ├─ ProcessPoolExecutor              │
│ ├─ ThreadPoolExecutor               │
│ ├─ concurrent.futures               │
└─ （无自定义包装）                     │
└─────────────────────────────────────┘
```

---

## 职责清晰对比

### backtest_scheduler（共享）

**调度特性**：
- 时间线/切片模式
- 队列填池策略
- 进程池执行
- Dispatch规划

**使用模块**：
- tag
- strategy

---

### data_source scheduler（内置）

**调度特性**：
- 依赖拓扑排序
- 串行执行（依赖注入）
- bundle并行抓取
- retry机制
- 线程池执行

**使用模块**：
- 仅data_source

---

## 为什么选择B（data_source内置）

### 调度逻辑完全不同

| 特性 | backtest_scheduler | data_source_scheduler |
|------|-------------------|----------------------|
| 执行顺序 | 时间线/切片 | 依赖拓扑 |
| 并行策略 | Queue/Batch | bundle并行 |
| 执行池 | ProcessPoolExecutor | ThreadPoolExecutor |
| 特殊逻辑 | Dispatch规划 | retry、依赖注入 |

### 强行合并的后果

如果选择A（合并成modules.scheduler）：

**问题**：
- scheduler既理解回测语义，又理解数据源语义
- 过度耦合，职责不清
- 未来维护困难（两个不同的调度逻辑混在一起）

**示例**：
```python
# 如果合并，scheduler变得复杂
class Scheduler:
    def schedule(self, tasks, mode):
        if mode == "backtest":
            # 时间线/切片逻辑
            return self._schedule_backtest(tasks)
        elif mode == "data_source":
            # 拓扑排序逻辑
            return self._schedule_data_source(tasks)
        # 职责不清，代码混乱
```

---

## 实施步骤

### Phase 1: 创建modules.backtest_scheduler空壳

```bash
core/modules/backtest_scheduler/
├─ module_info.yaml
├─ README.md
├─ __init__.py
├─ scheduler.py（空壳）
├─ dispatch_planner.py（空壳）
├─ dispatch_time_planner.py（空壳）
└─ types.py（空壳）
```

---

### Phase 2: 迁移dispatch规划

- infra.worker.dispatch_planner.py → modules.backtest_scheduler
- infra.worker.dispatch_time_planner.py → modules.backtest_scheduler
- 修改导入路径（strategy/tag）

---

### Phase 3: 迁移类型定义

- infra.worker.process_worker.py::JobResult → modules.backtest_scheduler.types
- infra.worker.process_worker.py::JobStatus → modules.backtest_scheduler.types

---

### Phase 4: 迁移job_pipeline核心

- infra.job_pipeline → modules.backtest_scheduler.scheduler
- 修改导入路径（strategy/tag）

---

### Phase 5: 废弃infra层

- 删除infra.worker（完全废弃）
- 删除infra.job_pipeline（迁移完成）

---

### Phase 6: data_source优化

- DataSourcePipelineRunner：直接用ThreadPoolExecutor
- 不依赖外部scheduler

---

## MQ迁移路径

### backtest_scheduler迁移

```python
# 当前
scheduler = LocalScheduler()  # ProcessPoolExecutor

# 未来
scheduler = MQScheduler(broker_url='amqp://localhost')
```

业务代码改2行即可。

---

### data_source保持独立

```python
# data_source不需要MQ
# 继续用ThreadPoolExecutor（足够轻量）
runner = DataSourcePipelineRunner()
runner.run_bundles(bundles)
```

---

## 总结

**核心决策**：

1. ✅ 废除worker模块（Python标准库足够）
2. ✅ 创建modules.backtest_scheduler（tag/strategy共用）
3. ✅ data_source内置scheduler（调度逻辑不同）

**理由**：

- **职责清晰**：每个scheduler专注自己的领域
- **架构正确**：调度逻辑不同，不应该强行合并
- **未来友好**：MQ迁移路径清晰

**原则**：

- 正确性胜过稳定性
- 职责归属决定位置
- 不打补丁

---

**下一步**：Phase 1 - 创建modules.backtest_scheduler空壳