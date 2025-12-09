# Data Source Handler 设计文档 v3.0（简化版）

**版本：** 2.0  
**日期：** 2025-01-XX  
**状态：** 设计阶段

---

## 📋 设计理念

### 核心思想

**简化设计，职责分离：**

```
Handler 职责：生成 Tasks（每个 Task 包含多个 ApiJobs）→ 框架执行
框架职责：展开 Tasks → 解析 ApiJob Schema → 决定执行策略 → 执行 → 按 Task 分组返回结果
```

### 设计原则

1. **Handler 简单化**：Handler 只需要生成 Tasks，不需要理解复杂的配置格式
2. **Task 层设计**：引入 Task 层，一个 Task 代表一个业务任务，更直观易理解
3. **框架智能化**：框架根据 ApiJob Schema 自动决定执行策略（串行/并行、限流、多线程）
4. **灵活性优先**：Handler 完全控制 Task 和 ApiJob 生成逻辑，支持复杂场景
5. **代码可读性**：直接看代码就知道在做什么，一个 Task 完整展示数据处理流程

---

## 🎯 核心组件

### 1. ApiJob 和 DataSourceTask 定义

**设计理念：**

- **ApiJob**：单个 API 调用任务（最小执行单元）
- **DataSourceTask**：业务任务（包含多个 ApiJobs，代表一个完整的数据处理流程）

这样设计的好处：
- **更直观**：一个 Task 代表一个业务任务（如"获取复权因子"），可以完整看到数据处理流程
- **更易理解**：不需要读很多代码就能理解一个 Task 包含哪些 API 调用
- **更易维护**：针对一只股票或一个日期产生的多个 API 调用，都在一个 Task 中

#### ApiJob 定义

```python
@dataclass
class ApiJob:
    """API Job 定义（带 Schema）"""
    # ========== 执行信息（必需）==========
    provider_name: str           # Provider 名称
    method: str                  # Provider 方法名
    params: Dict[str, Any]       # 调用参数（已计算好）
    
    # ========== 依赖关系（可选）==========
    depends_on: List[str] = []   # 依赖的 ApiJob ID 列表（用于决定执行顺序）
    
    # ========== 元信息（可选，用于框架决策）==========
    job_id: Optional[str] = None  # Job ID（用于依赖关系，自动生成）
    api_name: Optional[str] = None  # API 名称（用于限流，默认 = method）
    
    # ========== 可选配置 ==========
    priority: int = 0            # 优先级（数字越大越优先）
    timeout: Optional[float] = None  # 超时时间（秒）
    retry_count: int = 0         # 重试次数
```

#### DataSourceTask 定义

```python
@dataclass
class DataSourceTask:
    """DataSource Task 定义"""
    # ========== 任务信息（必需）==========
    task_id: str                 # Task ID（唯一标识）
    api_jobs: List[ApiJob]        # 包含的 ApiJobs 列表
    
    # ========== 可选配置 ==========
    description: Optional[str] = None  # Task 描述
    merge_callback: Optional[Callable] = None  # 合并回调函数（可选）
```

**关键字段说明：**

- **ApiJob**：
  - `provider_name` + `method`：指定调用哪个 Provider 的哪个方法
  - `params`：调用参数（**已计算好**，不需要占位符替换）
  - `depends_on`：依赖关系，框架会自动进行拓扑排序
  - `api_name`：用于限流，框架会从 Provider 获取该 API 的限流信息

- **DataSourceTask**：
  - `task_id`：Task 的唯一标识
  - `api_jobs`：包含的 ApiJobs 列表（一个 Task 可以包含多个 ApiJobs）
  - `description`：Task 描述（可选，用于文档和日志）
  - `merge_callback`：合并回调函数（可选，框架可以调用此函数合并 ApiJobs 的结果）

---

### 2. Handler 接口

**定义：** Handler 负责生成 Jobs，框架负责执行

```python
class BaseHandler(ABC):
    """
    简化的 Handler 设计
    
    Handler 只需要：
    1. 生成 Jobs（带 Schema）
    2. 返回原始数据
    """
    
    # ========== 类属性（子类必须定义）==========
    data_source: str = None          # 数据源名称
    renew_type: str = None           # "refresh" | "incremental" | "upsert"
    description: str = ""            # Handler 描述
    dependencies: List[str] = []      # 依赖的其他数据源
    
    def __init__(self, schema, params: Dict[str, Any] = None, data_manager=None):
        """
        初始化 Handler
        
        Args:
            schema: 数据源的 schema 定义
            params: 从 mapping.json 传入的自定义参数
            data_manager: 数据管理器（用于数据库查询）
        """
        self.schema = schema
        self.params = params or {}
        self.data_manager = data_manager
        self._providers = {}
    
    @abstractmethod
    async def fetch(self, context: Dict[str, Any]) -> List[DataSourceTask]:
        """
        生成 Tasks
        
        Args:
            context: 执行上下文，包含：
                - start_date: 开始日期（incremental 需要）
                - end_date: 结束日期（incremental 需要）
                - stock_codes: 股票代码列表（如果需要）
                - force_refresh: 是否强制刷新
                - ... 其他依赖数据源的数据
        
        Returns:
            List[DataSourceTask]: 一组编排好的 Tasks（每个 Task 包含多个 ApiJobs）
        
        注意：
        - Handler 完全控制 Task 和 ApiJob 生成逻辑
        - 可以查询数据库、计算参数、处理复杂逻辑
        - 参数必须已计算好（不需要占位符替换）
        - 一个 Task 代表一个业务任务（如：获取复权因子、获取股票 K 线）
        - 一个 Task 可以包含多个 ApiJobs（如：Tushare API + AKShare API）
        """
        pass
    
    @abstractmethod
    async def normalize(self, task_results: Dict[str, Dict[str, Any]]) -> Dict:
        """
        将原始数据标准化为框架 schema 格式
        
        Args:
            task_results: 框架执行 Tasks 后返回的结果字典 {task_id: {job_id: result}}
        
        Returns:
            标准化后的数据字典，格式符合 self.schema
        """
        pass
    
    # ========== 可选的钩子方法 ==========
    
    # ========== 数据准备阶段 ==========
    async def before_fetch(self, context: Dict[str, Any]):
        """
        获取数据前的钩子（可用于数据准备）
        
        可以用于：
        - 查询数据库获取上次更新时间
        - 计算参数
        - 准备执行上下文
        """
        pass
    
    async def after_fetch(self, tasks: List[DataSourceTask], context: Dict[str, Any]):
        """
        生成 Tasks 后的钩子（Tasks 还未执行）
        
        可以用于：
        - 验证 Tasks
        - 记录日志
        - 统计 Tasks 和 ApiJobs 数量
        """
        pass
    
    # ========== 执行阶段 ==========
    async def before_execute(self, tasks: List[DataSourceTask], context: Dict[str, Any]):
        """
        框架执行 Tasks 前的钩子
        
        可以用于：
        - 最后调整 Tasks 或 ApiJobs
        - 记录执行前的状态
        - 验证 Tasks 配置
        - 设置执行参数
        """
        pass
    
    async def after_execute(
        self, 
        task_results: Dict[str, Dict[str, Any]], 
        context: Dict[str, Any]
    ):
        """
        框架执行 Tasks 后的钩子（在 normalize 之前）
        
        可以用于：
        - 合并结果（按 Task 处理）
        - 计算业务逻辑（如复权因子计算）
        - 直接入库（如果不需要标准化）
        - 数据预处理
        
        Args:
            task_results: 框架执行 Tasks 后返回的结果字典 {task_id: {job_id: result}}
            context: 执行上下文
        
        注意：
        - 此时可以访问所有 Tasks 的执行结果
        - task_results 的结构：{task_id: {job_id: result}}
        - 可以修改 task_results，传递给后续的 normalize
        - 如果在这里入库，normalize 可能只需要返回格式化数据
        """
        pass
    
    # ========== 标准化阶段 ==========
    async def before_normalize(self, raw_data: Any):
        """
        标准化前的钩子
        
        可以用于：
        - 数据预处理
        - 数据验证
        """
        pass
    
    async def after_normalize(self, normalized_data: Dict):
        """
        标准化后的钩子
        
        可以用于：
        - 数据后处理
        - 记录日志
        """
        pass
    
    # ========== 错误处理 ==========
    async def on_error(self, error: Exception, context: Dict[str, Any]):
        """错误处理钩子"""
        pass
    
    # ========== 框架提供的工具方法 ==========
    
    async def execute_jobs(
        self, 
        jobs: List[Job],
        max_workers: Optional[int] = None,
        use_rate_limit: bool = True
    ) -> Dict[str, Any]:
        """
        执行一组 Jobs（框架提供）
        
        - 自动处理依赖关系（拓扑排序）
        - 自动应用限流
        - 自动决定线程数
        - 返回 {job_id: result} 字典
        
        注意：Handler 可以直接调用，也可以让框架自动调用
        """
        pass
```

---

### 3. 框架执行器（JobExecutor）

**定义：** 框架负责解析 Job Schema 并执行

```python
class JobExecutor:
    """
    框架执行器
    
    职责：
    1. 解析 Job Schema（依赖关系、限流信息等）
    2. 决定执行策略（串行/并行、线程数、限流）
    3. 执行 Jobs
    4. 收集结果
    """
    
    def __init__(self, providers: Dict[str, Provider], rate_limiter: RateLimiter):
        self.providers = providers
        self.rate_limiter = rate_limiter
    
    async def execute(self, jobs: List[Job]) -> Dict[str, Any]:
        """
        执行 Jobs
        
        流程：
        1. 为每个 Job 生成 job_id（如果未提供）
        2. 解析依赖关系（拓扑排序）
        3. 获取限流信息（从 Provider）
        4. 决定执行策略（线程数）
        5. 按阶段执行
        6. 返回结果 {job_id: result}
        """
        # 1. 生成 job_id
        self._assign_job_ids(jobs)
        
        # 2. 拓扑排序
        stages = self._topological_sort(jobs)
        
        # 3. 获取限流信息
        api_limits = self._collect_api_limits(jobs)
        
        # 4. 决定线程数
        workers = self._decide_workers(jobs, api_limits)
        
        # 5. 按阶段执行
        results = {}
        for stage in stages:
            if len(stage) == 1:
                # 单 Job，直接执行
                result = await self._execute_single_job(stage[0], api_limits)
                results[stage[0].job_id] = result
            else:
                # 多 Job，并行执行
                stage_results = await self._execute_parallel(stage, workers, api_limits)
                results.update(stage_results)
        
        return results
    
    def _topological_sort(self, jobs: List[Job]) -> List[List[Job]]:
        """
        拓扑排序，将 Jobs 分组为执行阶段
        
        返回：
            List[List[Job]]: 执行阶段列表，每个阶段内的 Jobs 可以并行执行
        
        示例：
            Jobs: [A, B(depends_on=[A]), C(depends_on=[A]), D(depends_on=[B, C])]
            返回: [[A], [B, C], [D]]
                 阶段0    阶段1    阶段2
        """
        # Kahn 算法实现
        pass
    
    def _collect_api_limits(self, jobs: List[Job]) -> Dict[str, int]:
        """
        收集所有 Jobs 的限流信息
        
        从 Provider 的 api_limits 中获取
        """
        pass
    
    def _decide_workers(self, jobs: List[Job], api_limits: Dict[str, int]) -> int:
        """
        决定线程数
        
        策略：
        1. 如果 Job 数量 < 10，使用单线程
        2. 根据最严格的 API 限流计算最大并发数（限流的 80%）
        3. 线程数不超过 Job 数量
        4. 应用最大/最小线程数限制
        """
        pass
```

---

## 📊 执行流程

```
1. 数据准备阶段
   ├─ before_fetch(context)  # 钩子：数据准备
   │  └─ 查询数据库、计算参数、准备执行上下文
   │
   ├─ Handler.fetch(context) → List[Job]
   │  └─ Handler 生成 Jobs（查询数据库、计算参数等）
   │
   └─ after_fetch(jobs, context)  # 钩子：Job 生成后（还未执行）
      └─ 验证 Jobs、记录日志

2. 执行阶段
   ├─ before_execute(jobs, context)  # 钩子：框架执行前
   │  └─ 最后调整 Jobs、设置执行参数
   │
   ├─ 框架执行（JobExecutor.execute(jobs)）
   │  ├─ 生成 job_id
   │  ├─ 拓扑排序（根据 depends_on）
   │  ├─ 获取限流信息（从 Provider）
   │  ├─ 决定线程数
   │  └─ 按阶段执行
   │     ├─ 阶段 0: [Job1, Job2] (并行)
   │     ├─ 阶段 1: [Job3] (单 Job)
   │     └─ 阶段 2: [Job4, Job5] (并行)
   │
   └─ after_execute(raw_data, context)  # 钩子：框架执行后
      └─ 合并结果、计算业务逻辑、直接入库
      └─ raw_data = {job_id: result}

3. 标准化阶段
   ├─ before_normalize(raw_data)  # 钩子：标准化前
   │
   ├─ Handler.normalize(raw_data) → Dict
   │  └─ 标准化数据（如果 after_execute 已入库，这里可能只是格式化）
   │
   └─ after_normalize(normalized_data)  # 钩子：标准化后
```

### 执行流程说明

**职责划分：**

- **Handler 职责**：
  - 生成 Tasks（`fetch()`，每个 Task 包含多个 ApiJobs）
  - 标准化数据（`normalize()`）
  - 业务逻辑处理（hooks）

- **框架职责**：
  - 展开 Tasks 为 ApiJobs
  - 执行 ApiJobs（`TaskExecutor.execute()`）
  - 处理依赖关系（拓扑排序）
  - 应用限流
  - 多线程管理
  - 按 Task 分组收集结果

**关键钩子：**

- `before_fetch`：数据准备（查询数据库、计算参数）
- `after_fetch`：Tasks 生成后（还未执行）
- `before_execute`：框架执行前（可以最后调整 Tasks）
- `after_execute`：框架执行后（可以合并结果、计算业务逻辑、直接入库）
- `before_normalize`：标准化前
- `normalize`：标准化数据
- `after_normalize`：标准化后

---

## 💡 使用示例

### 示例 1：简单的股票列表 Handler

```python
class StockListHandler(BaseDataSourceHandler):
    data_source = "stock_list"
    renew_type = "refresh"
    description = "获取股票列表"
    
    async def fetch(self, context: Dict[str, Any]) -> List[DataSourceTask]:
        # 生成一个简单的 Task（包含一个 ApiJob）
        task = DataSourceTask(
            task_id="stock_list_all",
            description="获取所有股票列表",
            api_jobs=[
                ApiJob(
                    provider_name="tushare",
                    method="get_stock_list",
                    params={},
                    depends_on=[],
                )
            ],
        )
        return [task]
    
    async def normalize(self, task_results: Dict[str, Dict[str, Any]]) -> Dict:
        # task_results 是 {task_id: {job_id: result}} 字典
        # 取第一个 Task 的第一个 ApiJob 的结果
        task_id = "stock_list_all"
        job_results = task_results.get(task_id, {})
        result = list(job_results.values())[0] if job_results else []
        
        # 标准化为 schema 格式
        normalized = []
        for item in result:
            normalized.append({
                "id": item["ts_code"],
                "name": item["name"],
                "industry": item.get("industry", "未知行业"),
                # ... 其他字段
            })
        return {"data": normalized}
```

### 示例 2：复杂的 K 线数据 Handler（增量更新）

```python
class StockKlineHandler(BaseDataSourceHandler):
    data_source = "stock_kline"
    renew_type = "incremental"
    description = "获取股票 K 线数据（日/周/月）"
    
    async def fetch(self, context: Dict[str, Any]) -> List[DataSourceTask]:
        # 1. 数据准备
        latest_trade_date = await self._get_latest_trade_date()
        stock_codes = context.get("stock_codes") or await self._get_stock_list()
        
        # 2. 生成 Tasks
        tasks = []
        for stock_code in stock_codes:
            # 查询数据库，获取上次更新时间
            last_updates = await self._query_last_updates(stock_code)
            
            # 创建一个 Task：获取股票 K 线（包含 3 个周期的 ApiJobs）
            api_jobs = []
            for period in ["daily", "weekly", "monthly"]:
                # 计算起始日期
                last_update = last_updates.get(period)
                start_date = self._calculate_start_date(last_update, latest_trade_date)
                
                # 如果不需要更新，跳过
                if not start_date:
                    continue
                
                # 创建 ApiJob
                api_job = ApiJob(
                    provider_name="tushare",
                    method=f"get_{period}_kline",
                    params={
                        "ts_code": stock_code,
                        "start_date": start_date,
                        "end_date": latest_trade_date,
                    },
                    api_name=f"get_{period}_kline",  # 用于限流
                    depends_on=[],  # 无依赖
                )
                api_jobs.append(api_job)
            
            # 如果该股票有需要更新的周期，创建 Task
            if api_jobs:
                task = DataSourceTask(
                    task_id=f"kline_{stock_code}",
                    description=f"获取股票 {stock_code} 的 K 线数据（日/周/月）",
                    api_jobs=api_jobs,
                )
                tasks.append(task)
        
        return tasks
    
    async def normalize(self, task_results: Dict[str, Dict[str, Any]]) -> Dict:
        # task_results 是 {task_id: {job_id: result}} 字典
        # 合并所有周期的数据
        all_klines = []
        for task_id, job_results in task_results.items():
            for job_id, result in job_results.items():
                for item in result:
                    all_klines.append({
                        "id": item["ts_code"],
                        "term": self._extract_term_from_job_id(job_id),
                        "date": item["trade_date"],
                        "open": item["open"],
                        "close": item["close"],
                        # ... 其他字段
                    })
        return {"data": all_klines}
    
    async def _query_last_updates(self, stock_code: str) -> Dict[str, str]:
        """查询数据库，获取上次更新时间"""
        model = self.data_manager.get_model("stock_kline")
        
        last_updates = {}
        for period in ["daily", "weekly", "monthly"]:
            latest = model.load_latest_by_stock_and_term(stock_code, period)
            last_updates[period] = latest["date"] if latest else None
        
        return last_updates
    
    def _calculate_start_date(self, last_update: Optional[str], latest_date: str) -> Optional[str]:
        """计算起始日期"""
        if not last_update:
            return "20200101"  # 默认起始日期
        
        # 计算下一个交易日
        next_date = self._get_next_trade_date(last_update)
        if next_date > latest_date:
            return None  # 不需要更新
        
        return next_date
```

### 示例 4：有依赖关系的 Handler

```python
class StockKlineWithBasicHandler(BaseHandler):
    """获取 K 线数据 + 基础指标（有依赖关系）"""
    
    async def fetch(self, context: Dict[str, Any]) -> List[Job]:
        jobs = []
        stock_codes = context.get("stock_codes", [])
        
        for stock_code in stock_codes:
            # Job 1: 获取 K 线数据
            kline_job = Job(
                provider_name="tushare",
                method="get_daily_kline",
                params={"ts_code": stock_code, ...},
                api_name="get_daily_kline",
                job_id=f"kline_{stock_code}",  # 手动指定 job_id
                depends_on=[],
            )
            jobs.append(kline_job)
            
            # Job 2: 获取基础指标（依赖 K 线数据）
            basic_job = Job(
                provider_name="tushare",
                method="get_daily_basic",
                params={"ts_code": stock_code, ...},
                api_name="get_daily_basic",
                job_id=f"basic_{stock_code}",
                depends_on=[f"kline_{stock_code}"],  # 依赖 K 线 Job
            )
            jobs.append(basic_job)
        
        return jobs
    
    async def normalize(self, raw_data: Dict[str, Any]) -> Dict:
        # 框架会自动保证依赖关系，basic_job 的结果会在 kline_job 之后
        # 可以安全地合并数据
        pass
```

---

## 🎯 设计优势

### 1. 简单直观

- **Handler 职责清晰**：只需要生成 Jobs，不需要理解复杂的配置格式
- **代码可读性强**：直接看代码就知道在做什么
- **学习成本低**：不需要理解拓扑排序、Job 展开等复杂概念

### 2. 灵活性高

- **完全控制**：Handler 完全控制 Job 生成逻辑
- **支持复杂场景**：可以查询数据库、计算参数、处理复杂逻辑
- **动态生成**：可以根据实际情况动态生成 Jobs

### 3. 框架复用

- **自动处理**：框架自动处理依赖关系、限流、多线程
- **统一策略**：所有 Handler 使用统一的执行策略
- **易于扩展**：框架可以统一添加新功能（如重试、超时等）

### 4. 易于调试

- **直接看代码**：不需要理解配置 → 解析 → 展开的复杂链路
- **清晰的执行流程**：框架的执行流程清晰可见
- **错误定位容易**：错误发生在哪个 Job 一目了然

---

## 🔄 与 v2.0 设计的对比

| 维度 | v2.0（配置驱动） | v3.0（简化版） |
|------|----------------|---------------|
| **复杂度** | 高（需要理解多个组件） | 低（直接写代码） |
| **学习成本** | 高 | 低 |
| **灵活性** | 中（需要扩展组件） | 高（完全控制） |
| **代码量** | 少（配置） | 多（代码） |
| **调试难度** | 高（配置 → 解析链路长） | 低（直接看代码） |
| **复用性** | 高（配置可复用） | 中（代码可复用） |
| **适用场景** | 简单、标准化的场景 | 复杂、定制化的场景 |

---

## 📝 待实现功能

1. **JobExecutor**：框架执行器
   - 拓扑排序
   - 限流管理
   - 多线程执行

2. **RateLimiter**：限流器
   - 线程安全的限流
   - 支持多 API 独立限流
   - 令牌桶算法

3. **错误处理**：
   - 重试机制
   - 失败 Job 的处理策略
   - 错误钩子

4. **结果合并**：
   - 根据 `group_id` 合并结果
   - 根据 `merge_strategy` 合并结果

---

## 🎓 总结

v3.0 设计通过简化 Handler 接口，引入 Task 层，将复杂的配置解析逻辑移交给框架，实现了：

- **简单**：Handler 只需要生成 Tasks（每个 Task 包含多个 ApiJobs）
- **直观**：一个 Task 代表一个业务任务，可以完整看到数据处理流程
- **灵活**：完全控制 Task 和 ApiJob 生成逻辑
- **强大**：框架自动处理技术细节（限流、多线程、依赖处理）
- **易用**：学习成本低，代码可读性强

### 关键设计点

1. **职责分离**：
   - Handler 负责生成 Jobs 和业务逻辑
   - 框架负责执行 Jobs 和技术细节（限流、多线程、依赖处理）

2. **执行流程清晰**：
   - 数据准备阶段：`before_fetch` → `fetch` → `after_fetch`
   - 执行阶段：`before_execute` → 框架执行 → `after_execute`
   - 标准化阶段：`before_normalize` → `normalize` → `after_normalize`

3. **关键钩子**：
   - `before_execute`：提供 context 和 jobs，可以在框架执行前最后调整
   - `after_execute`：提供执行结果，可以合并结果、计算业务逻辑、直接入库
   - 这两个钩子使得 Handler 可以在框架执行前后完全控制流程

4. **复杂场景支持**：
   - 复权因子计算：在 `after_execute` 中合并多个 API 结果并计算
   - 增量更新：在 `before_fetch` 中查询数据库，在 `fetch` 中生成 Jobs
   - 多 Provider 协作：通过 `depends_on` 和 `group_id` 组织 Jobs

这个设计更适合复杂、定制化的场景，同时保持了框架的复用性和统一性。

