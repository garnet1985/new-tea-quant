# API 执行计划系统设计文档

## 📋 设计思路

基于配置驱动的 API 执行计划系统，通过铺平的 API 配置数组，自动解析依赖关系、生成执行计划、展开 Job 列表，并智能决策线程数和限流策略。

## 🎯 核心组件

### 1. APIExecutionPlanParser（执行计划解析器）

**职责：**
- 解析 API 配置数组
- 验证依赖关系（检测循环依赖）
- 拓扑排序，生成执行阶段
- 收集需要的 Provider 列表

**输入格式：**
```python
api_plan = [
    {
        "name": "daily_kline",           # API 名称（用于依赖关系）
        "provider": "tushare",            # Provider 名称
        "method": "get_daily_kline",       # Provider 方法名
        "params": {                        # 调用参数（支持占位符）
            "ts_code": "{stock_code}",
            "start_date": "{start_date}",
        },
        "depends_on": [],                 # 依赖的 API 名称列表（空表示无依赖）
        "batch_by": "stock_code",         # 可选：按字段批量展开
        "merge_strategy": "left_join",    # 可选：合并策略
    },
    {
        "name": "daily_basic",
        "provider": "tushare",
        "method": "get_daily_basic",
        "params": {
            "ts_code": "{stock_code}",
            "start_date": "{start_date}",
        },
        "depends_on": ["daily_kline"],    # 依赖 daily_kline（会自动串行执行）
    }
]
```

**输出：**
- `ExecutionPlan`: 包含执行阶段列表、Provider 列表、总 Job 数量

### 2. JobExpander（Job 展开器）

**职责：**
- 将 API 配置展开为多个执行 Job
- 根据 `batch_by` 字段展开（如按股票代码批量）
- 解析参数占位符（`{stock_code}`, `{start_date}`, `{context.key}`）

**支持的占位符：**
- `{stock_code}`: 股票代码（如果 `batch_by="stock_code"`）
- `{start_date}`: 开始日期
- `{end_date}`: 结束日期
- `{context.key}`: 上下文中的其他值

**输出：**
- `Dict[int, List[ExpandedJob]]`: `{stage_id: [job1, job2, ...]}`

### 3. ThreadDecisionMaker（线程决策器）

**职责：**
- 根据 Job 数量决定是否使用多线程
- 根据 API 限流信息计算最优线程数
- 支持自动调整和手动配置

**决策逻辑：**
1. 如果 Job 数量 < `min_jobs_for_multithread`（默认 10），使用单线程
2. 如果启用自动调整：
   - 根据最严格的 API 限流计算最大并发数（限流的 80%）
   - 线程数不超过 Job 数量
   - 应用最大/最小线程数限制
3. 如果不自动调整，使用配置的最大线程数或 1

## 📊 执行流程

```
1. 定义 API 配置数组
   ↓
2. APIExecutionPlanParser.parse()
   - 解析配置
   - 验证依赖
   - 拓扑排序
   - 生成执行阶段
   ↓
3. JobExpander.expand()
   - 展开 Job（根据 batch_by）
   - 解析参数占位符
   ↓
4. ThreadDecisionMaker.decide()
   - 计算线程数
   ↓
5. 执行（待实现）
   - 按阶段执行
   - 处理并行/串行
   - 应用限流
   - 合并结果
```

## 🔄 拓扑排序示例

**输入：**
```python
api_plan = [
    {"name": "A", "depends_on": []},
    {"name": "B", "depends_on": ["A"]},
    {"name": "C", "depends_on": ["A"]},
    {"name": "D", "depends_on": ["B", "C"]},
]
```

**输出执行阶段：**
```
阶段 0: [A]           # 无依赖，可以立即执行
阶段 1: [B, C]        # B 和 C 都依赖 A，但彼此无依赖，可以并行执行
阶段 2: [D]           # D 依赖 B 和 C，必须等待阶段 1 完成
```

**注意：**
- 同一阶段的 API 总是可以并行执行（因为它们没有依赖关系）
- 不同阶段的 API 必须串行执行（后面的阶段依赖前面的阶段）
- 并行/串行关系由拓扑排序自动确定，无需手动指定

## 🧵 线程决策示例

**场景 1：Job 数量少**
```python
job_count = 5
api_limits = {"get_daily_kline": 100}
→ 线程数: 1（单线程）
```

**场景 2：Job 数量多，限流宽松**
```python
job_count = 100
api_limits = {"get_daily_kline": 100}
→ 线程数: 80（100 * 0.8，不超过 job_count）
```

**场景 3：Job 数量多，限流严格**
```python
job_count = 100
api_limits = {"get_daily_kline": 50}
→ 线程数: 40（50 * 0.8，不超过 job_count）
```

## 📝 使用示例

```python
from app.data_source.utils.api_execution_plan import (
    APIExecutionPlanParser,
    JobExpander,
    ThreadDecisionMaker,
)

# 1. 定义 API 配置
api_plan = [
    {
        "name": "daily_kline",
        "provider": "tushare",
        "method": "get_daily_kline",
        "params": {"ts_code": "{stock_code}", "start_date": "20240101"},
        "depends_on": [],
        "batch_by": "stock_code",
    },
]

# 2. 解析执行计划
parser = APIExecutionPlanParser(api_plan)
execution_plan = parser.parse()

# 3. 展开 Job
context = {
    "stock_codes": ["000001.SZ", "000002.SZ"],
    "start_date": "20240101",
    "end_date": "20241231",
}
expander = JobExpander(execution_plan, context)
expanded_jobs = expander.expand()

# 4. 决策线程数
thread_decider = ThreadDecisionMaker({
    "min_jobs_for_multithread": 10,
    "max_workers": None,  # 自动计算
})
total_jobs = sum(len(jobs) for jobs in expanded_jobs.values())
api_limits = {"get_daily_kline": 100}  # 从 Provider 获取
workers = thread_decider.decide(total_jobs, api_limits)

print(f"总 Job 数: {total_jobs}")
print(f"线程数: {workers}")
```

## 🚧 待实现功能

1. **执行器（Executor）**
   - 按阶段执行 Job
   - 处理并行/串行
   - 应用限流
   - 收集结果

2. **限流管理器（RateLimiter）**
   - 线程安全的限流器
   - 支持多 API 独立限流
   - 令牌桶算法

3. **结果合并器（ResultMerger）**
   - 根据 `merge_strategy` 合并结果
   - 支持 `left_join`, `union`, `concat` 等策略

4. **错误处理**
   - 重试机制
   - 失败 Job 的处理策略
   - 错误钩子

## 📌 设计要点

1. **配置驱动**：通过配置定义 API 调用计划，无需硬编码
2. **自动解析**：自动解析依赖关系，使用拓扑排序确定执行顺序
3. **智能决策**：根据 Job 数量和 API 限流自动决策线程数
4. **灵活扩展**：支持单 Provider 多 API、多 Provider 等复杂场景
5. **占位符支持**：参数支持占位符，便于批量处理

