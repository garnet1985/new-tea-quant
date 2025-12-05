# Data Provider 架构设计文档

## 文档目的

本文档是经过完整讨论后的最终设计方案，包含所有核心设计决策和实施指南。

---

## 📋 讨论总结

### 讨论的核心问题

1. ✅ **依赖关系硬编码** → 声明式依赖 + 自动协调
2. ✅ **Provider接口不统一** → BaseProvider统一接口
3. ✅ **缺乏数据协调层** → DataCoordinator自动处理
4. ✅ **限流机制设计** → API级别限流（不是data_type级别）
5. ✅ **多周期数据粒度** → 独立data_type + 组合语法糖
6. ✅ **手动干预能力** → 三层灵活性（自动/半自动/手动）
7. ✅ **可发现性** → 运行时查询API + 命令行工具
8. ✅ **多线程与性能** → 保留并迁移有用组件

### 核心设计决策

| 决策 | 原因 | 影响 |
|-----|------|------|
| **全新架构（不适配Legacy）** | 彻底解耦，避免历史包袱 | 需要重写，但架构清晰 |
| **API级别限流** | 一个data_type可能调用多个API | 支持智能并发策略 |
| **独立data_type** | 灵活性 + 精确依赖 | 可单独更新任意周期 |
| **智能并发** | 处理多API限流差异 | 自适应串行/并行 |
| **声明式依赖** | 可扩展性 + 可维护性 | 新增Provider无需改代码 |

---

## 🏗️ 架构设计

### 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                 应用层 (start.py)                        │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│          DataProviderManager (统一管理器)                │
│  - 初始化 Registry & Coordinator                        │
│  - 提供统一的更新入口                                    │
└────────┬────────────────────┬────────────────────────────┘
         │                    │
┌────────▼──────────┐  ┌──────▼──────────────────────────┐
│ ProviderRegistry  │  │   DataCoordinator               │
│ (动态挂载)         │  │   - 解析依赖关系                │
│                   │◄─┤   - 计算执行顺序                │
│ - mount()         │  │   - 构建执行上下文              │
│ - unmount()       │  │   - 协调多Provider              │
│ - get()           │  └─────────────────────────────────┘
└────────┬──────────┘
         │
┌────────▼─────────────────────────────────────────────────┐
│          RateLimitRegistry (API限流注册表)                │
│  - 管理所有API的限流器                                    │
│  - API级别限流（不是data_type级别）                       │
└──────────────────────────────────────────────────────────┘
         │
┌────────▼─────────────────────────────────────────────────┐
│               BaseProvider (统一接口)                     │
│  - get_provider_info()  返回元数据                       │
│  - renew_all()          更新所有数据                      │
│  - renew_data_type()    更新指定类型                      │
└──────┬───────────────────────────┬───────────────────────┘
       │                           │
┌──────▼──────────┐       ┌────────▼──────────┐
│ TushareProvider │       │ AKShareProvider   │
│ (重写)          │       │ (重写)            │
└─────────────────┘       └───────────────────┘
```

---

## 🎯 核心组件设计

### 1. BaseProvider（统一接口）

```python
# app/data_provider/core/base_provider.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class Dependency:
    """依赖声明"""
    provider: str                      # 依赖的Provider名称
    data_types: List[str]              # 依赖的数据类型
    when: str = "before_renew"         # before_renew | runtime
    required: bool = True              # 是否必需
    pass_data: bool = False            # 是否传递数据

@dataclass
class ProviderInfo:
    """Provider元数据"""
    name: str                          # Provider名称
    version: str = "1.0.0"             # 版本
    provides: List[str] = None         # 提供的数据类型
    dependencies: List[Dependency] = None  # 依赖关系
    requires_auth: bool = False        # 是否需要认证

@dataclass
class ExecutionContext:
    """执行上下文"""
    end_date: str                      # 截止日期
    stock_list: List[str] = None       # 股票列表
    dependencies: Dict[str, Any] = None  # 依赖数据
    config: Dict[str, Any] = None      # 额外配置

class BaseProvider(ABC):
    """Provider统一接口"""
    
    def __init__(self, data_manager, rate_limit_registry):
        self.data_manager = data_manager
        self.rate_limit_registry = rate_limit_registry
    
    # ===== 必须实现 =====
    
    @abstractmethod
    def get_provider_info(self) -> ProviderInfo:
        """返回Provider元数据"""
        pass
    
    @abstractmethod
    async def renew_all(self, end_date: str, context: ExecutionContext = None):
        """更新所有数据类型"""
        pass
    
    @abstractmethod
    def supports_data_type(self, data_type: str) -> bool:
        """是否支持某种数据类型"""
        pass
    
    # ===== 可选实现 =====
    
    async def renew_data_type(self, data_type: str, end_date: str, 
                             context: ExecutionContext = None):
        """更新指定数据类型（可选）"""
        return await self.renew_all(end_date, context)
```

---

### 2. RateLimitRegistry（API限流注册表）⭐ 核心创新

```python
# app/data_provider/core/rate_limit_registry.py

class APIRateLimiter:
    """
    单个API的限流器（令牌桶算法）
    
    ⭐ 线程安全
    """
    
    def __init__(self, api_identifier: str, max_per_minute: int, buffer: int = 5):
        self.api_identifier = api_identifier
        self.max_per_minute = max_per_minute
        self.buffer = buffer
        self.tokens = max_per_minute
        self.last_update = time.time()
        self._lock = threading.Lock()
    
    def acquire(self, count: int = 1):
        """获取令牌（阻塞直到获得）"""
        with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            
            if elapsed > 0:
                new_tokens = elapsed * (self.max_per_minute / 60.0)
                self.tokens = min(self.max_per_minute, self.tokens + new_tokens)
                self.last_update = now
            
            if self.tokens >= count:
                self.tokens -= count
                return
            
            wait_time = (count - self.tokens) * (60.0 / self.max_per_minute)
            logger.warning(f"⏰ API [{self.api_identifier}] 限流等待 {wait_time:.2f}s")
        
        time.sleep(wait_time)
        self.acquire(count)


class RateLimitRegistry:
    """
    API限流注册表
    
    ⭐ 关键设计：
    - 限流对象是API，不是data_type
    - 统一管理所有API的限流器
    - 支持Provider注册自己的API限流
    """
    
    def __init__(self):
        self._limiters: Dict[str, APIRateLimiter] = {}
        self._lock = threading.Lock()
    
    def register_api(self, api_identifier: str, max_per_minute: int, buffer: int = 5):
        """
        注册API限流器
        
        Args:
            api_identifier: API唯一标识（如 'tushare.daily'）
            max_per_minute: 最大请求数/分钟
        """
        with self._lock:
            if api_identifier in self._limiters:
                return
            
            self._limiters[api_identifier] = APIRateLimiter(
                api_identifier, max_per_minute, buffer
            )
            logger.info(f"✅ API [{api_identifier}] 限流器已注册：{max_per_minute}次/分钟")
    
    def acquire(self, api_identifier: str, count: int = 1):
        """获取API令牌"""
        if api_identifier not in self._limiters:
            logger.warning(f"⚠️  API [{api_identifier}] 未注册限流器")
            return
        
        self._limiters[api_identifier].acquire(count)
```

---

### 3. ProviderRegistry（动态挂载）

```python
# app/data_provider/core/provider_registry.py

class ProviderRegistry:
    """Provider注册表"""
    
    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._data_type_index: Dict[str, List[str]] = {}
    
    def mount(self, name: str, provider: BaseProvider):
        """挂载Provider"""
        self._providers[name] = provider
        
        # 自动构建data_type索引
        info = provider.get_provider_info()
        for data_type in info.provides:
            if data_type not in self._data_type_index:
                self._data_type_index[data_type] = []
            self._data_type_index[data_type].append(name)
        
        logger.info(f"✅ Provider '{name}' 已挂载")
    
    def get(self, name: str) -> BaseProvider:
        """获取Provider实例"""
        return self._providers.get(name)
    
    def get_providers_for(self, data_type: str) -> List[str]:
        """获取支持某data_type的所有Provider"""
        return self._data_type_index.get(data_type, [])
```

---

### 4. DataCoordinator（协调器）

```python
# app/data_provider/core/data_coordinator.py

class DataCoordinator:
    """
    数据协调器
    
    职责：
    1. 解析依赖关系
    2. 计算执行顺序（拓扑排序）
    3. 确保依赖满足
    4. 构建执行上下文
    """
    
    def __init__(self, registry: ProviderRegistry, data_manager):
        self.registry = registry
        self.data_manager = data_manager
    
    def resolve_execution_order(self) -> List[str]:
        """
        计算执行顺序（拓扑排序）
        
        Returns:
            Provider名称列表，按依赖顺序
        """
        graph = self._build_dependency_graph()
        return graph.topological_sort()
    
    async def renew_all_providers(self, end_date: str):
        """更新所有Provider（按依赖顺序）"""
        order = self.resolve_execution_order()
        
        for provider_name in order:
            provider = self.registry.get(provider_name)
            context = await self._build_context(provider_name, end_date)
            await provider.renew_all(end_date, context)
    
    async def coordinate_update(self, data_type: str, end_date: str):
        """
        协调某个数据类型的更新
        
        ⭐ 自动处理依赖：
        1. 找到负责的Provider
        2. 检查依赖是否满足
        3. 递归更新依赖
        4. 执行更新
        """
        providers = self.registry.get_providers_for(data_type)
        provider_name = providers[0]
        provider = self.registry.get(provider_name)
        
        # 获取依赖
        info = provider.get_provider_info()
        
        # 确保依赖满足
        for dep in info.dependencies:
            if dep.when == "before_renew":
                for dep_data_type in dep.data_types:
                    if not await self._is_data_available(dep_data_type, end_date):
                        # 递归更新依赖
                        await self.coordinate_update(dep_data_type, end_date)
        
        # 构建上下文
        context = await self._build_context(provider_name, end_date)
        
        # 执行更新
        await provider.renew_data_type(data_type, end_date, context)
```

---

### 5. SmartConcurrentExecutor（智能并发）⭐ 处理多API限流

```python
# app/data_provider/core/smart_concurrent.py

class SmartConcurrentExecutor:
    """
    智能并发执行器
    
    ⭐ 解决问题：
    - 一个data_type可能调用多个API
    - 不同API限流速率不同
    - 需要智能选择串行/并行策略
    """
    
    def __init__(self, rate_limit_registry: RateLimitRegistry):
        self.rate_limit_registry = rate_limit_registry
    
    async def execute_multi_api_jobs(
        self,
        jobs_by_api: Dict[str, List[Dict]],
        executor_by_api: Dict[str, Callable],
        strategy: str = "adaptive"
    ):
        """
        执行多个API的任务
        
        策略：
        - sequential: 串行（简单安全）
        - parallel: 并行（需要协调）
        - adaptive: 自适应（根据限流速率自动选择）
        """
        if strategy == "adaptive":
            return await self._execute_adaptive(jobs_by_api, executor_by_api)
        elif strategy == "sequential":
            return await self._execute_sequential(jobs_by_api, executor_by_api)
        elif strategy == "parallel":
            return await self._execute_parallel(jobs_by_api, executor_by_api)
    
    async def _execute_adaptive(self, jobs_by_api, executor_by_api):
        """
        自适应策略
        
        规则：
        - 如果API限流速率相近 → 并行
        - 如果有明显瓶颈API → 串行
        """
        # 分析限流速率
        rates = {}
        for api_id in jobs_by_api.keys():
            limiter = self.rate_limit_registry.get_limiter(api_id)
            rates[api_id] = limiter.max_per_minute if limiter else 1000
        
        min_rate = min(rates.values())
        max_rate = max(rates.values())
        
        # 判断
        if max_rate / min_rate < 2:
            logger.info("📊 使用并行策略（API限流相近）")
            return await self._execute_parallel(jobs_by_api, executor_by_api)
        else:
            logger.info("📊 使用串行策略（API限流差异大）")
            return await self._execute_sequential(jobs_by_api, executor_by_api)
```

---

## 📊 Provider实现示例

### TushareProvider完整示例

```python
# app/data_provider/providers/tushare/tushare_provider.py

class TushareProvider(BaseProvider):
    """
    Tushare Provider
    
    特点：
    1. 注册所有API的限流
    2. 支持多周期K线（独立 + 组合）
    3. 使用智能并发处理多API
    """
    
    def __init__(self, data_manager, rate_limit_registry):
        super().__init__(data_manager, rate_limit_registry)
        
        # 初始化API
        self.api = ts.pro_api()
        
        # 注册API限流
        self._register_api_rate_limits()
    
    def _register_api_rate_limits(self):
        """注册所有API的限流"""
        # K线API
        self.rate_limit_registry.register_api('tushare.daily', max_per_minute=100)
        self.rate_limit_registry.register_api('tushare.weekly', max_per_minute=50)
        self.rate_limit_registry.register_api('tushare.monthly', max_per_minute=30)
        
        # 财务API
        self.rate_limit_registry.register_api('tushare.income', max_per_minute=200)
        self.rate_limit_registry.register_api('tushare.balancesheet', max_per_minute=200)
        
        # 宏观API
        self.rate_limit_registry.register_api('tushare.cn_gdp', max_per_minute=200)
    
    def get_provider_info(self):
        return ProviderInfo(
            name="tushare",
            version="1.0.0",
            provides=[
                # 基础数据
                "stock_list",
                
                # K线（独立周期）
                "stock_kline_daily",
                "stock_kline_weekly",
                "stock_kline_monthly",
                
                # K线（组合）
                "stock_kline_all",
                
                # 其他
                "corporate_finance",
                "gdp",
                "cpi",
                "ppi",
                "pmi",
                "shibor",
                "lpr"
            ],
            dependencies=[]  # Tushare无依赖
        )
    
    async def renew_data_type(self, data_type: str, end_date: str, context: ExecutionContext):
        """更新指定数据类型"""
        
        if data_type == "stock_kline_daily":
            return await self._renew_kline_single(end_date, context.stock_list, 'daily')
        
        elif data_type == "stock_kline_weekly":
            return await self._renew_kline_single(end_date, context.stock_list, 'weekly')
        
        elif data_type == "stock_kline_monthly":
            return await self._renew_kline_single(end_date, context.stock_list, 'monthly')
        
        elif data_type == "stock_kline_all":
            return await self._renew_kline_all(end_date, context.stock_list)
    
    async def _renew_kline_single(self, end_date: str, stock_list: List[str], freq: str):
        """更新单个周期的K线"""
        api_map = {
            'daily': 'tushare.daily',
            'weekly': 'tushare.weekly',
            'monthly': 'tushare.monthly'
        }
        api_id = api_map[freq]
        
        # 构建任务
        jobs = [{'ts_code': code, 'end_date': end_date} for code in stock_list]
        
        # 执行（多线程 + 限流）
        async def execute_job(job):
            # ⭐ API限流
            self.rate_limit_registry.acquire(api_id)
            
            # 调用API
            df = self.api.daily(ts_code=job['ts_code'], end_date=job['end_date'])
            
            # 保存数据
            self._save_data(df, freq)
        
        await self._execute_concurrent(jobs, execute_job, max_workers=4)
    
    async def _renew_kline_all(self, end_date: str, stock_list: List[str]):
        """
        更新所有周期（智能并发）
        
        ⭐ 使用SmartConcurrentExecutor处理多API限流
        """
        from app.data_provider.core.smart_concurrent import SmartConcurrentExecutor
        
        executor = SmartConcurrentExecutor(self.rate_limit_registry)
        
        # 构建任务
        jobs_by_api = {
            'tushare.daily': [{'ts_code': c, 'end_date': end_date} for c in stock_list],
            'tushare.weekly': [{'ts_code': c, 'end_date': end_date} for c in stock_list],
            'tushare.monthly': [{'ts_code': c, 'end_date': end_date} for c in stock_list]
        }
        
        # 构建执行器
        executor_by_api = {
            'tushare.daily': lambda job: self._execute_job(job, 'daily'),
            'tushare.weekly': lambda job: self._execute_job(job, 'weekly'),
            'tushare.monthly': lambda job: self._execute_job(job, 'monthly')
        }
        
        # ⭐ 智能并发执行
        # 自动分析：100/50/30，差异大，使用串行
        results = await executor.execute_multi_api_jobs(
            jobs_by_api,
            executor_by_api,
            strategy='adaptive'
        )
        
        return results
```

---

## 🎯 数据类型粒度设计

### 独立 data_type + 组合语法糖

```python
# K线数据：独立周期
"stock_kline_daily"      # 日线（独立）
"stock_kline_weekly"     # 周线（独立）
"stock_kline_monthly"    # 月线（独立）

# K线数据：组合
"stock_kline_all"        # 包含日/周/月（语法糖）

# 使用场景：
# 1. 只更新日线
await provider.renew_data_type('stock_kline_daily', end_date, context)

# 2. 更新所有周期
await provider.renew_data_type('stock_kline_all', end_date, context)

# 3. 自定义组合
await provider.renew_data_type('stock_kline_daily', end_date, context)
await provider.renew_data_type('stock_kline_monthly', end_date, context)
# 跳过周线
```

### 依赖关系示例

```python
# AKShare的复权因子只依赖日线（不依赖周线和月线）
class AKShareProvider(BaseProvider):
    def get_provider_info(self):
        return ProviderInfo(
            name="akshare",
            provides=["adj_factor"],
            dependencies=[
                Dependency(
                    provider="tushare",
                    data_types=["stock_kline_daily"],  # ⭐ 只依赖日线
                    when="before_renew",
                    required=True
                )
            ]
        )
```

---

## 🛠️ 从Legacy迁移的工具

### 1. 并发执行器

```python
# app/data_provider/utils/concurrent_executor.py

# 从 utils/worker/multi_thread/futures_worker.py 迁移
class ConcurrentExecutor:
    """并发执行器（线程安全）"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
    
    async def execute(self, jobs: List[Dict], executor: Callable):
        """执行任务（多线程）"""
        # 保留FuturesWorker的核心逻辑
        pass
```

### 2. 进度跟踪器

```python
# app/data_provider/utils/progress_tracker.py

# 从 utils/progress/progress_tracker.py 迁移
class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self, total: int):
        self.total = total
        self.completed = 0
        self._lock = threading.Lock()
    
    def update(self, count: int = 1):
        """更新进度（线程安全）"""
        with self._lock:
            self.completed += count
            progress = (self.completed / self.total) * 100
            logger.info(f"进度: {progress:.1f}%")
```

### 3. 增量更新工具

```python
# app/data_provider/utils/incremental_updater.py

# 从 BaseRenewer.should_renew() 迁移
class IncrementalUpdater:
    """增量更新工具"""
    
    def build_jobs(self, end_date: str, db_records: List[Dict]):
        """
        构建增量任务
        
        ⭐ 保留逻辑：
        - 计算下一个周期
        - 处理披露延迟
        - 区分新股票和老股票
        """
        pass
```

### 4. 字段映射工具

```python
# app/data_provider/utils/data_mapper.py

# 从 BaseRenewer.map_api_data() 迁移
class DataMapper:
    """数据映射工具"""
    
    def map(self, data, mapping: Dict):
        """
        映射字段
        
        支持：
        - 简单映射: "db_field": "api_field"
        - 转换函数: {"source": "x", "transform": lambda x: x * 100}
        - 默认值: {"source": "x", "default": 0}
        """
        pass
```

---

## 📋 目录结构

```
app/data_provider/
├── core/                           # 核心组件
│   ├── __init__.py
│   ├── base_provider.py            # BaseProvider接口
│   ├── rate_limit_registry.py      # ⭐ API限流注册表
│   ├── smart_concurrent.py         # ⭐ 智能并发执行器
│   ├── provider_registry.py        # Provider注册表
│   └── data_coordinator.py         # 数据协调器
│
├── providers/                      # 各个Provider（重写）
│   ├── __init__.py
│   ├── tushare/
│   │   ├── __init__.py
│   │   ├── tushare_provider.py     # ⭐ 主类
│   │   ├── api_client.py           # API客户端封装
│   │   └── config.yaml             # 配置
│   │
│   └── akshare/
│       ├── __init__.py
│       ├── akshare_provider.py     # ⭐ 主类
│       └── config.yaml
│
├── utils/                          # 工具类（从Legacy迁移）
│   ├── __init__.py
│   ├── concurrent_executor.py      # 多线程工具
│   ├── progress_tracker.py         # 进度跟踪
│   ├── incremental_updater.py      # 增量更新
│   └── data_mapper.py              # 字段映射
│
├── config/                         # 配置文件
│   ├── data_provider.yaml          # 全局配置
│   └── providers/
│       ├── tushare.yaml
│       └── akshare.yaml
│
├── __init__.py
├── DESIGN.md                       # 本文档
└── README.md                       # 使用指南
```

---

## 🚀 实施计划

### Phase 1: 核心组件（3-4天）

**目标：** 实现框架基础

```
□ BaseProvider接口
□ RateLimitRegistry（API限流）
□ ProviderRegistry（动态挂载）
□ DataCoordinator（协调器）
□ SmartConcurrentExecutor（智能并发）
```

### Phase 2: 工具迁移（2-3天）

**目标：** 从Legacy迁移有用组件

```
□ ConcurrentExecutor（多线程）
□ ProgressTracker（进度跟踪）
□ IncrementalUpdater（增量更新）
□ DataMapper（字段映射）
```

### Phase 3: TushareProvider（3-4天）

**目标：** 实现第一个完整Provider

```
□ 基础框架
□ API限流注册
□ K线多周期支持
□ 财务数据支持
□ 宏观数据支持
□ 测试验证
```

### Phase 4: AKShareProvider（2-3天）

**目标：** 实现第二个Provider并验证依赖

```
□ 基础框架
□ 复权因子实现
□ 依赖声明（依赖Tushare K线）
□ 测试依赖协调
```

### Phase 5: 集成测试（2-3天）

**目标：** 完整测试和优化

```
□ 单Provider测试
□ 多Provider依赖测试
□ 性能测试
□ 限流测试
□ 边界情况测试
```

---

## 🎯 使用示例

### 初始化

```python
from app.data_provider.core.rate_limit_registry import RateLimitRegistry
from app.data_provider.core.provider_registry import ProviderRegistry
from app.data_provider.core.data_coordinator import DataCoordinator
from app.data_provider.providers.tushare.tushare_provider import TushareProvider
from app.data_provider.providers.akshare.akshare_provider import AKShareProvider

# 1. 创建限流注册表
rate_limit_registry = RateLimitRegistry()

# 2. 创建Provider注册表
provider_registry = ProviderRegistry()

# 3. 挂载Provider
tushare = TushareProvider(data_manager, rate_limit_registry)
provider_registry.mount('tushare', tushare)

akshare = AKShareProvider(data_manager, rate_limit_registry)
provider_registry.mount('akshare', akshare)

# 4. 创建协调器
coordinator = DataCoordinator(provider_registry, data_manager)
```

### 使用：更新所有数据

```python
# 自动按依赖顺序执行
await coordinator.renew_all_providers(end_date='20250101')

# ✅ 自动执行：
# 1. tushare: 更新stock_list, stock_kline（akshare依赖）
# 2. akshare: 更新adj_factor
```

### 使用：更新指定数据

```python
# 只更新复权因子（自动处理依赖）
await coordinator.coordinate_update('adj_factor', end_date='20250101')

# ✅ 自动处理：
# 1. 检查: stock_kline_daily是否可用
# 2. 如果不可用 → 先更新K线
# 3. 然后更新复权因子
```

### 使用：灵活控制

```python
# Level 2: 半自动（跳过依赖检查）
await coordinator.coordinate_update(
    'adj_factor',
    end_date='20250101',
    skip_dependency_check=True  # 我知道依赖已满足
)

# Level 3: 完全手动
tushare = provider_registry.get('tushare')
await tushare.renew_data_type('stock_kline_daily', end_date, context)
```

---

## 🔍 可发现性（查询API）

```python
# 列出所有data_type
all_types = coordinator.list_all_data_types()
# ['stock_kline_daily', 'stock_kline_weekly', 'adj_factor', ...]

# 查询Provider能力
caps = coordinator.get_provider_capabilities('tushare')
# {'provides': [...], 'dependencies': [...]}

# 查询data_type详情
info = coordinator.get_data_type_info('adj_factor')
# {'providers': ['akshare'], 'dependencies': [{'provider': 'tushare', ...}]}

# 查询依赖链
chain = coordinator.get_dependency_chain('adj_factor')
# ['stock_list', 'stock_kline_daily', 'adj_factor']

# 打印系统摘要
coordinator.print_summary()
```

---

## 📊 配置文件示例

```yaml
# config/data_provider/tushare.yaml

provider: tushare
enabled: true

# API限流配置
api_rate_limits:
  daily:
    max_per_minute: 100
    buffer: 5
  
  weekly:
    max_per_minute: 50
  
  monthly:
    max_per_minute: 30
  
  income:
    max_per_minute: 200

# 数据类型配置
data_types:
  stock_kline_daily:
    apis: [daily]
    concurrent: true
    max_workers: 4
  
  stock_kline_all:
    apis: [daily, weekly, monthly]
    strategy: adaptive  # ⭐ 自适应策略
```

---

## 🎯 核心设计思想

### 1. 统一接口 + 动态扩展

```
BaseProvider = 统一接口
ProviderRegistry = 动态挂载
DataCoordinator = 自动协调

新增Provider = 实现接口 + mount() → 自动工作
```

### 2. API级别限流（不是data_type级别）

```
限流对象 = API（tushare.daily, tushare.weekly）
一个data_type可能调用多个API
SmartConcurrentExecutor处理多API限流协调
```

### 3. 声明式依赖 + 自动协调

```
Provider声明依赖 → Registry构建索引 → Coordinator自动协调

零硬编码！完全动态！
```

### 4. 多层次灵活性

```
Level 1: 完全自动（99%场景）
Level 2: 半自动控制（可选参数）
Level 3: 完全手动（Hack接口）
```

### 5. 独立data_type + 组合语法糖

```
独立: stock_kline_daily, stock_kline_weekly, stock_kline_monthly
组合: stock_kline_all（语法糖，调用上面三个）

灵活性 + 便利性！
```

---

## ✅ 设计优势总结

| 特性 | 旧架构 | 新架构 | 改进 |
|-----|--------|--------|------|
| **依赖管理** | 硬编码 | 声明式 | ⭐⭐⭐⭐⭐ |
| **限流机制** | data_type级别 | API级别 | ⭐⭐⭐⭐⭐ |
| **多API协调** | 不支持 | 智能并发 | ⭐⭐⭐⭐⭐ |
| **新增Provider** | 修改代码 | 实现接口+配置 | ⭐⭐⭐⭐⭐ |
| **接口一致性** | 不一致 | 统一 | ⭐⭐⭐⭐⭐ |
| **可发现性** | 无 | 查询API+命令行 | ⭐⭐⭐⭐ |
| **灵活性** | 低 | 三层灵活性 | ⭐⭐⭐⭐ |
| **测试性** | 难 | 易于Mock | ⭐⭐⭐⭐ |
| **多线程** | 保留 | 迁移保留 | ⭐⭐⭐⭐ |
| **进度跟踪** | 保留 | 迁移保留 | ⭐⭐⭐⭐ |

---

## 📝 关键决策记录

### 决策1: 全新架构 vs 适配器

**选择：** 全新架构（app/data_provider/）

**原因：**
- 彻底解耦，避免历史包袱
- 架构清晰，易于理解和扩展
- 迁移有用组件，保留核心能力

### 决策2: API级别限流 vs data_type级别

**选择：** API级别限流

**原因：**
- 一个data_type可能调用多个API
- 不同API限流速率不同
- 支持智能并发策略

### 决策3: 独立data_type vs 组合data_type

**选择：** 独立 + 组合（语法糖）

**原因：**
- 灵活性：可单独更新任意周期
- 便利性：提供组合语法糖
- 精确依赖：复权因子只依赖日线

### 决策4: 串行 vs 并行 vs 自适应

**选择：** 自适应策略

**原因：**
- 限流速率相近 → 并行（快）
- 限流速率差异大 → 串行（避免瓶颈）
- 自动选择，无需手动配置

---

**最后更新：** 2025-12-05  
**维护者：** @garnet  
**状态：** 设计完成，待实施

