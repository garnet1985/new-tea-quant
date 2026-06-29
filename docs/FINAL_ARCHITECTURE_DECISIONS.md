# 最终架构决策

---

## 1. Worker模块定位

**不迁移dispatch规划函数**（留在infra.worker）

**理由**：
- 当前稳定，迁移风险大
- 通过Facade提供快捷访问，已经足够好
- 未来可以在backtest_scheduler里创建代理调用

**Worker模块最终职责**：
```
infra.worker：
├─ Dispatch规划辅助功能（核心）
│  ├─ resolve_dispatch_plan（内存预算规划）
│  ├─ resolve_time_dispatch_plan（时间预算规划）
│  ├─ resolve_memory_budget_mb（内存预算）
│  ├─ should_run_dispatch_probe（是否运行探针）
│
├─ 类型定义
│  ├─ DispatchPlan
│  ├─ TimeDispatchPlan
│  ├─ JobResult
│  ├─ JobStatus
│
└─ Facade（Worker类）
   └─ 提快捷访问入口
```

---

## 2. Backtest Scheduler模块命名

**不创建modules.backtest_scheduler**（保持当前job_pipeline）

**理由**：
- 当前job_pipeline已经实现调度功能
- 重命名和迁移风险大
- 保持稳定，不做大重构

**JobPipeline定位调整**：
- 明确为"业务调度层"，不属于infra
- 但暂时保留在infra.job_pipeline（避免大重构）
- 文档中说明定位，实际位置不动

---

## 3. DataSource多线程处理

**不需要单独pipeline**（Python标准库足够）

**理由**：
- DataSource是串行调度（依赖顺序）
- 不需要复杂的并发调度
- ThreadPoolExecutor(max_workers=1)足够

---

## 4. MQ迁移方案

**最简化方案**（不需要抽象接口层）

```python
# 当前（轻量级）
from core.infra.job_pipeline import JobPipeline
pipeline = JobPipeline(...)
pipeline.run(jobs)

# 未来（MQ）
from core.modules.backtest.mq_runner import MQBacktestRunner
runner = MQBacktestRunner(...)
runner.run(jobs)
```

**业务代码迁移成本**：改2行即可

---

## 最终架构（稳定优先）

```text
当前架构（保持稳定）：

infra.worker（辅助工具）
├─ Dispatch规划函数
├─ 类型定义
└─ Facade

infra.job_pipeline（业务调度）
├─ 队列填池策略
├─ on_result回调
└─ JobContext封装
定位：业务调度层（文档说明）

modules（业务层）
├─ tag/strategy：使用job_pipeline + worker.dispatch规划
└─ data_source：串行调度（不需要pipeline）
```

**不做大重构的理由**：
- 当前架构已经稳定（370个测试通过）
- 迁移风险大（job_pipeline被多处使用）
- 保持稳定，文档说明定位即可
- 未来MQ迁移成本极低（改2行代码）

---

## 总结

**三个问题答案**：

1. **Dispatch规划函数迁移**：不迁移（风险大，留在worker）
2. **模块命名**：不改名（保持job_pipeline，文档说明定位）
3. **DataSource多线程**：不需要pipeline（Python标准库足够）

**核心原则**：
- 稳定优先（不做大重构）
- 文档说明定位（明确职责边界）
- MQ迁移友好（未来改2行即可）

**下一步**：
- 完善文档（明确职责边界）
- 保持当前架构稳定
- 未来需要MQ时再实施迁移