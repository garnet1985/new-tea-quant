# Backtest Scheduler 规范

**版本**：`0.1.0`
**定位**：回测引擎（业务调度层，不属于infra）

---

## 1. 核心定位

**Scheduler是什么**：
- 回测引擎（Backtest Engine）
- 业务调度层（modules层，理解回测语义）
- 统一处理timeline和sliced两种回测机制

**Scheduler不是什么**：
- 不是infra层（不提供通用执行框架）
- 不是业务逻辑层（不实现Tag/Strategy的具体计算）
- 不是持久化层（不负责MQ、数据库等）

---

## 2. 边界定义

### 2.1 Scheduler职责（In Scope）

**核心职责**：
- 调度回测任务（timeline/sliced两种模式）
- 管理Worker生命周期钩子（job前、job中、job后）
- 执行并发逻辑（切割jobs、分配进程、执行）
- 汇报结果（on_result回调）

**具体职责**：

**Timeline模式调度**：
- Probe 粗估 + Plan 定 `entities_per_job`（全 run 固定）与 `max_workers` 上限
- Monitor 每 N job 汇总采样，**仅动态调整 in-flight workers**
- 切割 jobs 成 batch，经 `TimelineExecutePipeline` 进程池执行
- 每个 batch 结束 `on_result` 汇报

详见 [TIMELINE_EXECUTION.md](./TIMELINE_EXECUTION.md)。

**Sliced模式调度**：
- 使用探针决定读取queue大小和reader数量
- 分层调度：Reader（多进程） + Compute（单进程）
- 累计至少2个slice后开始计算和预读取
- 全程有一个结果对象收集结果
- slice完成后汇报结果

**生命周期管理**：
- Job前：调用Worker.on_before_jobs（类方法，主进程）
- Job中：调用Worker.run（实例方法，子进程）
- Job后：调用Worker.on_after_jobs（类方法，主进程）

---

### 2.2 Scheduler边界（Out of Scope）

**不负责业务逻辑**：
- 不知道Tag计算什么指标
- 不知道Strategy计算什么因子
- 不实现calculate_tag/find_opportunity等业务钩子

**不负责数据操作**：
- 不加载历史数据（Worker负责）
- 不保存结果数据（Worker/Manager负责）
- 不理解数据结构（Worker负责）

**不负责持久化调度**：
- 不持久化任务队列（MQ负责）
- 不实现分布式调度（MQ负责）
- 不持久化任务状态（MQ负责）

**不负责配置解析**：
- 不解析worker.json（Manager负责）
- 不解析scenario配置（Manager负责）
- 不理解配置语义（Manager负责）

---

## 3. Input定义

### 3.1 必需参数

**jobs: List[Job]**
```python
jobs = [
    {
        "id": "job_1",
        "entity_id": "stock_001",
        "payload": {...},        # Worker需要的业务数据
        "worker_class_name": "MyTagWorker",
        "worker_module_path": "my_tag_worker.py",
    },
    ...
]
```

**mode: str**
```python
mode = "timeline"  # 或 "sliced"
```

**worker_class: Type[BaseWorker]**
```python
worker_class = MyTagWorker  # 继承BaseTagWorker/BaseStrategyWorker
```

**performance: Dict[str, Any]**
```python
performance = {
    "max_workers": 4,
    "entities_per_job": 5,
    "dispatch_probe": True,
    "memory_budget_mb": 4096,
    ...
}
```

---

### 3.2 可选参数

**scenario_model: ScenarioModel**
```python
scenario_model = ScenarioModel(...)  # 用于Worker.on_before_jobs/on_after_jobs
```

**settings: Dict[str, Any]**
```python
settings = {...}  # Worker需要的配置
```

**on_result: Callable**
```python
on_result = lambda result: save_result(result)  # 结果回调（可选）
```

---

## 4. Output定义

### 4.1 主输出

**results: List[Dict[str, Any]]**
```python
results = [
    {
        "job_id": "job_1",
        "entity_id": "stock_001",
        "success": True,
        "data": {...},          # Worker返回的业务结果
        "errors": [],
        "stats": {
            "execution_time": 1.23,
            "memory_used": 256,
        },
    },
    ...
]
```

---

### 4.2 统计输出（可选）

**stats: Dict[str, Any]**
```python
stats = {
    "total_jobs": 100,
    "success_count": 95,
    "failure_count": 5,
    "total_time": 120.5,
    "avg_time_per_job": 1.2,
    "max_memory_used": 512,
}
```

---

## 5. API设计

### 5.1 Scheduler核心API

```python
class BacktestScheduler:
    """
    回测引擎（Backtest Engine）
    
    职责：调度回测任务，管理Worker生命周期
    """
    
    def run(
        self,
        jobs: List[Dict[str, Any]],
        mode: str,
        worker_class: Type[BaseWorker],
        performance: Dict[str, Any],
        scenario_model: Optional[ScenarioModel] = None,
        settings: Optional[Dict[str, Any]] = None,
        on_result: Optional[Callable] = None,
    ) -> List[Dict[str, Any]]:
        """
        执行回测调度
        
        Args:
            jobs: 待执行的job列表
            mode: 执行模式（"timeline" 或 "sliced"）
            worker_class: 业务逻辑类（继承BaseWorker）
            performance: 调度配置
            scenario_model: 场景模型（可选）
            settings: Worker配置（可选）
            on_result: 结果回调（可选）
        
        Returns:
            所有job的执行结果列表
        """
        
        # ===== Job前（主进程） =====
        worker_class.on_before_jobs(
            scenario_model=scenario_model,
            entity_list=[job["entity_id"] for job in jobs],
            settings=settings,
        )
        
        # ===== Job中（子进程） =====
        results = self._execute_jobs(
            jobs=jobs,
            mode=mode,
            worker_class=worker_class,
            performance=performance,
        )
        
        # ===== Job后（主进程） =====
        worker_class.on_after_jobs(
            results=results,
            scenario_model=scenario_model,
            settings=settings,
        )
        
        return results
```

---

### 5.2 Timeline模式内部实现

```python
def _execute_timeline_jobs(
    self,
    jobs: List[Dict[str, Any]],
    worker_class: Type[BaseWorker],
    performance: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Timeline模式调度实现"""
    
    # 1. 使用探针决定bundle大小和进程数
    dispatch_plan = resolve_dispatch_plan(
        total_entities=len(jobs),
        performance=performance,
    )
    
    # 2. 切割jobs成bundle
    bundles = self._bundle_jobs(
        jobs=jobs,
        entities_per_job=dispatch_plan.entities_per_job,
    )
    
    # 3. 执行（ProcessPoolExecutor）
    executor = ProcessPoolExecutor(
        max_workers=dispatch_plan.max_workers,
    )
    
    results = []
    for bundle in bundles:
        bundle_results = executor.map(
            lambda job: worker_class(job).run(),
            bundle,
        )
        results.extend(bundle_results)
        
        # 每个bundle结束call一次on_result
        if on_result:
            for result in bundle_results:
                on_result(result)
    
    executor.shutdown()
    return results
```

---

### 5.3 Sliced模式内部实现

```python
def _execute_sliced_jobs(
    self,
    jobs: List[Dict[str, Any]],
    worker_class: Type[BaseWorker],
    performance: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Sliced模式调度实现"""
    
    # 1. 使用探针决定reader数量和queue大小
    runtime_plan = build_runtime_plan(
        jobs=jobs,
        performance=performance,
    )
    
    # 2. 分层调度：Reader（多进程） + Compute（单进程）
    orchestrator = SliceOrchestrator(
        jobs=jobs,
        worker_class=worker_class,
        runtime_plan=runtime_plan,
    )
    
    # 3. 执行Reader ∥ Compute编排
    results = orchestrator.run()
    
    # 4. 汇报结果
    if on_result:
        on_result(results)
    
    return results
```

---

## 6. Worker钩子管理

### 6.1 Worker钩子分类

**类方法钩子（主进程调用）**：
```python
@classmethod
def on_before_jobs(cls, scenario_model, entity_list, settings):
    """Job前钩子（主进程）"""
    return filtered_entity_list

@classmethod
def on_after_jobs(cls, results, scenario_model, settings):
    """Job后钩子（主进程）"""
    pass
```

**实例方法钩子（子进程调用）**：
```python
def on_init(self):
    """初始化钩子（子进程）"""
    pass

def calculate_tag(self, as_of_date, historical_data, tag_definition):
    """核心计算钩子（子进程，必须实现）"""
    pass

def on_after_execute_tagging(self, result):
    """Job完成钩子（子进程）"""
    pass
```

---

### 6.2 Scheduler调用时机

**完整生命周期**：
```text
Scheduler.run() {
    # ===== Job前（主进程） =====
    worker_class.on_before_jobs(...)        # Manager调用Worker类方法
    
    # ===== Job中（子进程） =====
    for job in jobs:
        worker = worker_class(job)          # 子进程创建实例
        worker.on_init()                    # 子进程调用实例方法
        worker.calculate_tag(...)           # 子进程调用实例方法
        worker.on_after_execute_tagging()   # 子进程调用实例方法
        result = worker.run()
        on_result(result)                   # Manager回调
    
    # ===== Job后（主进程） =====
    worker_class.on_after_jobs(...)         # Manager调用Worker类方法
}
```

---

## 7. MQ迁移路径

### 7.1 迁移方式

**配置切换（无需改代码）**：
```python
# worker.json配置
{
    "scheduler": {
        "type": "mq",  # 从"local"改成"mq"
        "broker_url": "amqp://localhost"
    }
}
```

**Scheduler内部替换（唯一需要改的）**：
```python
class BacktestScheduler:
    def run(self, jobs, mode, worker_class, performance):
        scheduler_type = performance.get("scheduler", {}).get("type", "local")
        
        if scheduler_type == "local":
            # ProcessPoolExecutor（当前）
            executor = ProcessPoolExecutor(...)
            results = executor.map(...)
        elif scheduler_type == "mq":
            # MQ（未来）
            mq_client = MQClient(...)
            mq_client.submit_jobs(jobs, worker_class)
            results = mq_client.wait_results()
        
        return results
```

---

### 7.2 迁移成本

**需要改的地方**：
- Scheduler内部实现：1个文件修改
- 配置新增：1行配置

**不需要改的地方**：
- Scheduler API：完全不变
- Manager调用：完全不变
- Worker基类：完全不变
- 用户代码：完全不变

---

## 8. 设计原则

### 8.1 核心原则

**用户简洁性优先**：
- 用户只继承BaseWorker
- 用户只实现钩子函数
- 用户不关心执行细节（主进程/子进程）

**职责清晰分离**：
- Scheduler：调度 + 生命周期管理
- Worker：业务逻辑 + 钩子实现
- Manager：配置 + 调用Scheduler

**扩展性友好**：
- MQ迁移极简（配置切换）
- 新调度模式易扩展（新增mode）
- 新Worker类型易扩展（继承BaseWorker）

---

### 8.2 架构分层

```text
用户层：继承BaseWorker，实现钩子
    ↓
Manager层：配置解析，调用Scheduler
    ↓
Scheduler层：调度 + 生命周期管理
    ↓
执行层：ProcessPoolExecutor / MQ
    ↓
Worker层：业务逻辑 + 钩子执行
```

---

## 9. 与现有架构的对比

### 9.1 现有架构

```text
TagManager/Pipeline
    ↓ 自己调度
infra.job_pipeline
    ↓ 执行框架
infra.worker
    ↓ 辅助工具
```

**问题**：
- 调度逻辑分散在Manager/Pipeline
- job_pipeline定位不清（infra层但理解业务）
- worker职责混乱（多进程废弃但还有辅助功能）

---

### 9.2 新架构

```text
TagManager/StrategyManager
    ↓ 调用Scheduler
modules.backtest_scheduler
    ↓ 调度 + 生命周期管理
ProcessPoolExecutor / MQ
    ↓ 执行
Worker
    ↓ 业务逻辑
```

**优势**：
- 调度逻辑集中在Scheduler
- Scheduler定位清晰（回测引擎）
- Worker职责清晰（业务逻辑）
- MQ迁移友好

---

## 10. 实施路径

### Phase 1: 架构设计（已完成）
- 创建modules/backtest_scheduler空壳
- 定义职责边界、Input/Output

### Phase 2: 提取Tag调度逻辑
- timeline调度逻辑迁移到Scheduler
- TagManager调用Scheduler

### Phase 3: 提取Strategy调度逻辑
- timeline/sliced调度逻辑迁移到Scheduler
- StrategyManager调用Scheduler

### Phase 4: 清理旧架构
- 删除infra.job_pipeline
- 删除infra.worker（保留辅助功能到shared）

---

## 总结

**Scheduler是回测引擎**：
- 核心职责：调度 + 生命周期管理
- Input：jobs + mode + worker_class
- Output：results + stats
- MQ迁移：极简（配置切换）
- 用户体验：简洁（继承BaseWorker）