# 限流机制重新设计

## 问题分析

### 你的观察完全正确！⭐

**限流是针对 API 的，不是针对 action 的！**

---

## 🔥 问题场景

### 场景：renew K线所有周期

```python
# 假设：
# - 日线API: 100次/分钟
# - 周线API: 50次/分钟
# - 月线API: 30次/分钟

# ❌ 错误理解：每个data_type独立限流
await renew_data_type('stock_kline_daily')    # 限流100次/分钟
await renew_data_type('stock_kline_weekly')   # 限流50次/分钟
await renew_data_type('stock_kline_monthly')  # 限流30次/分钟

# 问题：如果串行执行，最慢的API（30次/分钟）会成为瓶颈
# 但其他API的限流器不知道这一点！

# ✅ 正确理解：API级别限流
# 需要一个统一的API限流管理器
# 管理所有API的限流，确保不超限
```

---

## 🎯 新设计：API级别的限流管理

### 核心思想

```
限流对象 = API（不是data_type）

一个data_type可能调用多个API
一个API可能被多个data_type使用
```

---

## 📐 新架构设计

### 1. API限流注册表

```python
# app/data_provider/core/rate_limit_registry.py

from typing import Dict
import threading
from loguru import logger

class APIRateLimiter:
    """
    单个API的限流器（令牌桶算法）
    
    ⭐ 线程安全
    """
    
    def __init__(
        self, 
        api_identifier: str,      # API唯一标识
        max_per_minute: int,      # 最大请求数/分钟
        buffer: int = 5           # 缓冲区
    ):
        self.api_identifier = api_identifier
        self.max_per_minute = max_per_minute
        self.buffer = buffer
        
        # 令牌桶
        self.tokens = max_per_minute
        self.last_update = time.time()
        
        # 线程锁
        self._lock = threading.Lock()
        
        # 统计
        self._request_count = 0
        self._throttle_count = 0
    
    def acquire(self, count: int = 1):
        """
        获取令牌
        
        Args:
            count: 需要的令牌数（默认1）
        """
        with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            
            if elapsed > 0:
                # 补充令牌
                new_tokens = elapsed * (self.max_per_minute / 60.0)
                self.tokens = min(self.max_per_minute, self.tokens + new_tokens)
                self.last_update = now
            
            # 检查令牌
            if self.tokens >= count:
                self.tokens -= count
                self._request_count += count
                return
            
            # 需要等待
            wait_time = (count - self.tokens) * (60.0 / self.max_per_minute)
            self._throttle_count += 1
            
            logger.warning(
                f"⏰ API [{self.api_identifier}] 触发限流，"
                f"等待 {wait_time:.2f}s（已限流 {self._throttle_count} 次）"
            )
        
        # 释放锁后等待
        time.sleep(wait_time)
        self.acquire(count)


class RateLimitRegistry:
    """
    API限流注册表
    
    ⭐ 统一管理所有API的限流器
    """
    
    def __init__(self):
        self._limiters: Dict[str, APIRateLimiter] = {}
        self._lock = threading.Lock()
    
    def register_api(
        self, 
        api_identifier: str,
        max_per_minute: int,
        buffer: int = 5
    ):
        """
        注册API限流器
        
        Args:
            api_identifier: API唯一标识（如 'tushare.daily'）
            max_per_minute: 最大请求数/分钟
            buffer: 缓冲区
        """
        with self._lock:
            if api_identifier in self._limiters:
                logger.warning(f"⚠️  API [{api_identifier}] 已注册，跳过")
                return
            
            self._limiters[api_identifier] = APIRateLimiter(
                api_identifier=api_identifier,
                max_per_minute=max_per_minute,
                buffer=buffer
            )
            
            logger.info(
                f"✅ API [{api_identifier}] 限流器已注册：{max_per_minute}次/分钟"
            )
    
    def acquire(self, api_identifier: str, count: int = 1):
        """
        获取API令牌
        
        Args:
            api_identifier: API标识
            count: 需要的令牌数
        """
        if api_identifier not in self._limiters:
            logger.warning(
                f"⚠️  API [{api_identifier}] 未注册限流器，跳过限流"
            )
            return
        
        limiter = self._limiters[api_identifier]
        limiter.acquire(count)
    
    def get_limiter(self, api_identifier: str) -> APIRateLimiter:
        """获取限流器"""
        return self._limiters.get(api_identifier)
    
    def list_apis(self) -> List[str]:
        """列出所有已注册的API"""
        return list(self._limiters.keys())
```

---

### 2. Provider注册API限流

```python
# app/data_provider/providers/tushare/tushare_provider.py

class TushareProvider(BaseProvider):
    """
    Tushare Provider
    
    ⭐ 注册所有API的限流
    """
    
    def __init__(self, data_manager, rate_limit_registry: RateLimitRegistry):
        super().__init__(data_manager)
        self.rate_limit_registry = rate_limit_registry
        
        # === 注册所有API的限流 ===
        self._register_api_rate_limits()
        
        # 初始化API客户端
        self.api = ts.pro_api()
    
    def _register_api_rate_limits(self):
        """注册所有API的限流"""
        
        # K线相关API
        self.rate_limit_registry.register_api(
            'tushare.daily',        # 日线API
            max_per_minute=100      # ⭐ 100次/分钟
        )
        
        self.rate_limit_registry.register_api(
            'tushare.weekly',       # 周线API
            max_per_minute=50       # ⭐ 50次/分钟
        )
        
        self.rate_limit_registry.register_api(
            'tushare.monthly',      # 月线API
            max_per_minute=30       # ⭐ 30次/分钟
        )
        
        # 财务相关API
        self.rate_limit_registry.register_api(
            'tushare.income',       # 利润表
            max_per_minute=200
        )
        
        self.rate_limit_registry.register_api(
            'tushare.balancesheet', # 资产负债表
            max_per_minute=200
        )
        
        # 宏观经济API
        self.rate_limit_registry.register_api(
            'tushare.cn_gdp',       # GDP
            max_per_minute=200
        )
        
        # ... 注册其他API
    
    def get_provider_info(self):
        return ProviderInfo(
            name="tushare",
            provides=[
                "stock_kline_daily",
                "stock_kline_weekly",
                "stock_kline_monthly",
                "stock_kline_all",
                # ...
            ]
        )
    
    async def renew_data_type(self, data_type: str, end_date: str, context: ExecutionContext):
        """更新指定数据类型"""
        
        if data_type == "stock_kline_daily":
            return await self._renew_kline_daily(end_date, context.stock_list)
        
        elif data_type == "stock_kline_weekly":
            return await self._renew_kline_weekly(end_date, context.stock_list)
        
        elif data_type == "stock_kline_monthly":
            return await self._renew_kline_monthly(end_date, context.stock_list)
        
        elif data_type == "stock_kline_all":
            # ⭐ 组合：调用多个API
            return await self._renew_kline_all(end_date, context.stock_list)
    
    async def _renew_kline_daily(self, end_date: str, stock_list: List[str]):
        """更新日线（单个API）"""
        
        # 构建任务
        jobs = [{'ts_code': code, 'end_date': end_date} for code in stock_list]
        
        # 并发执行
        async def execute_job(job):
            # ⭐ 使用API限流
            self.rate_limit_registry.acquire('tushare.daily')
            
            # 调用API
            df = self.api.daily(
                ts_code=job['ts_code'],
                end_date=job['end_date']
            )
            
            # 保存数据
            self._save_kline_data(df, 'daily')
        
        # 多线程执行
        await self._execute_concurrent(jobs, execute_job, max_workers=4)
    
    async def _renew_kline_weekly(self, end_date: str, stock_list: List[str]):
        """更新周线（单个API）"""
        
        jobs = [{'ts_code': code, 'end_date': end_date} for code in stock_list]
        
        async def execute_job(job):
            # ⭐ 使用API限流（不同的API）
            self.rate_limit_registry.acquire('tushare.weekly')
            
            df = self.api.weekly(
                ts_code=job['ts_code'],
                end_date=job['end_date']
            )
            
            self._save_kline_data(df, 'weekly')
        
        await self._execute_concurrent(jobs, execute_job, max_workers=4)
    
    async def _renew_kline_monthly(self, end_date: str, stock_list: List[str]):
        """更新月线（单个API）"""
        
        jobs = [{'ts_code': code, 'end_date': end_date} for code in stock_list]
        
        async def execute_job(job):
            # ⭐ 使用API限流（最慢的API）
            self.rate_limit_registry.acquire('tushare.monthly')
            
            df = self.api.monthly(
                ts_code=job['ts_code'],
                end_date=job['end_date']
            )
            
            self._save_kline_data(df, 'monthly')
        
        await self._execute_concurrent(jobs, execute_job, max_workers=4)
    
    async def _renew_kline_all(self, end_date: str, stock_list: List[str]):
        """
        更新所有周期（组合）
        
        ⭐ 关键：需要考虑多个API的限流
        """
        logger.info("📊 更新所有K线周期（日/周/月）")
        
        # ⭐ 方案1：串行执行（简单但慢）
        await self._renew_kline_daily(end_date, stock_list)
        await self._renew_kline_weekly(end_date, stock_list)
        await self._renew_kline_monthly(end_date, stock_list)
        
        # 问题：每个API独立限流，总时间 = sum(各API时间)
        # 优点：简单，安全
        
        # ⭐ 方案2：智能并发（复杂但快）
        # 见下文
```

---

### 3. 智能并发策略（处理多API限流）

```python
# app/data_provider/core/smart_concurrent.py

class SmartConcurrentExecutor:
    """
    智能并发执行器
    
    ⭐ 处理多个API的限流协调
    """
    
    def __init__(self, rate_limit_registry: RateLimitRegistry):
        self.rate_limit_registry = rate_limit_registry
    
    async def execute_multi_api_jobs(
        self,
        jobs_by_api: Dict[str, List[Dict]],  # {api_identifier: [jobs]}
        executor_by_api: Dict[str, Callable], # {api_identifier: executor_func}
        strategy: str = "sequential"          # sequential | parallel | adaptive
    ):
        """
        执行多个API的任务
        
        Args:
            jobs_by_api: 按API分组的任务
            executor_by_api: 每个API的执行器
            strategy: 执行策略
        """
        
        if strategy == "sequential":
            # ⭐ 策略1：串行执行（简单安全）
            return await self._execute_sequential(jobs_by_api, executor_by_api)
        
        elif strategy == "parallel":
            # ⭐ 策略2：并行执行（需要协调）
            return await self._execute_parallel(jobs_by_api, executor_by_api)
        
        elif strategy == "adaptive":
            # ⭐ 策略3：自适应（智能选择）
            return await self._execute_adaptive(jobs_by_api, executor_by_api)
    
    async def _execute_sequential(self, jobs_by_api, executor_by_api):
        """
        串行执行
        
        ⭐ 简单安全，但慢
        """
        results = {}
        
        for api_id, jobs in jobs_by_api.items():
            logger.info(f"▶️  执行API [{api_id}]，共 {len(jobs)} 个任务")
            
            executor = executor_by_api[api_id]
            results[api_id] = await self._execute_jobs(jobs, executor)
        
        return results
    
    async def _execute_parallel(self, jobs_by_api, executor_by_api):
        """
        并行执行
        
        ⭐ 快但需要协调限流
        
        挑战：
        - 日线API：100次/分钟（快）
        - 周线API：50次/分钟（中）
        - 月线API：30次/分钟（慢）
        
        如果并行执行，需要确保：
        - 日线不会占用所有资源
        - 月线不会被饿死
        """
        import asyncio
        
        # 为每个API创建独立的任务
        tasks = []
        
        for api_id, jobs in jobs_by_api.items():
            executor = executor_by_api[api_id]
            
            # 创建任务
            task = asyncio.create_task(
                self._execute_jobs_with_fairness(api_id, jobs, executor)
            )
            tasks.append(task)
        
        # 并发执行
        results = await asyncio.gather(*tasks)
        
        return dict(zip(jobs_by_api.keys(), results))
    
    async def _execute_jobs_with_fairness(
        self, 
        api_id: str, 
        jobs: List[Dict],
        executor: Callable
    ):
        """
        执行任务（带公平性保证）
        
        ⭐ 确保慢API不会被快API饿死
        """
        limiter = self.rate_limit_registry.get_limiter(api_id)
        
        # 根据限流速率计算合理的并发数
        # 限流慢 → 并发数小
        # 限流快 → 并发数大
        max_workers = min(4, limiter.max_per_minute // 20)  # 简化计算
        
        # 执行
        return await self._execute_jobs(jobs, executor, max_workers=max_workers)
    
    async def _execute_adaptive(self, jobs_by_api, executor_by_api):
        """
        自适应策略
        
        ⭐ 根据API限流情况智能选择
        
        规则：
        - 如果所有API限流差不多 → 并行
        - 如果有明显瓶颈API → 串行
        - 如果任务量小 → 串行（简单）
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
            # 速率差异小 → 并行
            logger.info("📊 使用并行策略（API限流相近）")
            return await self._execute_parallel(jobs_by_api, executor_by_api)
        else:
            # 速率差异大 → 串行
            logger.info("📊 使用串行策略（API限流差异大）")
            return await self._execute_sequential(jobs_by_api, executor_by_api)
```

---

### 4. 使用智能并发

```python
# app/data_provider/providers/tushare/tushare_provider.py

class TushareProvider(BaseProvider):
    
    async def _renew_kline_all(self, end_date: str, stock_list: List[str]):
        """
        更新所有周期（智能并发）
        
        ⭐ 使用SmartConcurrentExecutor处理多API限流
        """
        from app.data_provider.core.smart_concurrent import SmartConcurrentExecutor
        
        executor = SmartConcurrentExecutor(self.rate_limit_registry)
        
        # 构建任务
        jobs_by_api = {
            'tushare.daily': [
                {'ts_code': code, 'end_date': end_date} 
                for code in stock_list
            ],
            'tushare.weekly': [
                {'ts_code': code, 'end_date': end_date}
                for code in stock_list
            ],
            'tushare.monthly': [
                {'ts_code': code, 'end_date': end_date}
                for code in stock_list
            ]
        }
        
        # 构建执行器
        executor_by_api = {
            'tushare.daily': lambda job: self._execute_daily_job(job),
            'tushare.weekly': lambda job: self._execute_weekly_job(job),
            'tushare.monthly': lambda job: self._execute_monthly_job(job)
        }
        
        # ⭐ 智能并发执行
        results = await executor.execute_multi_api_jobs(
            jobs_by_api,
            executor_by_api,
            strategy='adaptive'  # 自适应策略
        )
        
        logger.info("✅ 所有K线周期更新完成")
        return results
    
    def _execute_daily_job(self, job):
        """执行日线任务"""
        # 限流
        self.rate_limit_registry.acquire('tushare.daily')
        
        # 调用API
        df = self.api.daily(ts_code=job['ts_code'], end_date=job['end_date'])
        
        # 保存
        self._save_kline_data(df, 'daily')
    
    def _execute_weekly_job(self, job):
        """执行周线任务"""
        self.rate_limit_registry.acquire('tushare.weekly')
        df = self.api.weekly(ts_code=job['ts_code'], end_date=job['end_date'])
        self._save_kline_data(df, 'weekly')
    
    def _execute_monthly_job(self, job):
        """执行月线任务"""
        self.rate_limit_registry.acquire('tushare.monthly')
        df = self.api.monthly(ts_code=job['ts_code'], end_date=job['end_date'])
        self._save_kline_data(df, 'monthly')
```

---

## 📊 配置文件

```yaml
# config/data_provider/tushare.yaml

provider: tushare
enabled: true

# API限流配置
api_rate_limits:
  # K线API
  daily:
    max_per_minute: 100
    buffer: 5
  
  weekly:
    max_per_minute: 50
    buffer: 5
  
  monthly:
    max_per_minute: 30
    buffer: 5
  
  # 财务API
  income:
    max_per_minute: 200
  
  balancesheet:
    max_per_minute: 200
  
  cashflow:
    max_per_minute: 200
  
  # 宏观API
  cn_gdp:
    max_per_minute: 200

# 数据类型配置
data_types:
  stock_kline_daily:
    apis: [daily]  # 使用的API
    concurrent: true
    max_workers: 4
  
  stock_kline_weekly:
    apis: [weekly]
    concurrent: true
    max_workers: 4
  
  stock_kline_monthly:
    apis: [monthly]
    concurrent: true
    max_workers: 4
  
  stock_kline_all:
    apis: [daily, weekly, monthly]  # ⭐ 多个API
    strategy: adaptive  # ⭐ 自适应策略
```

---

## 🎯 新目录结构

```
app/data_provider/              # ⭐ 新文件夹
├── core/                       # 核心组件
│   ├── __init__.py
│   ├── base_provider.py        # BaseProvider接口
│   ├── rate_limit_registry.py  # ⭐ API限流注册表
│   ├── smart_concurrent.py     # ⭐ 智能并发执行器
│   ├── provider_registry.py    # Provider注册表
│   └── data_coordinator.py     # 数据协调器
│
├── providers/                  # 各个Provider
│   ├── tushare/
│   │   ├── __init__.py
│   │   ├── tushare_provider.py     # ⭐ 重写
│   │   ├── api_client.py           # API客户端封装
│   │   └── config.yaml             # 配置
│   │
│   ├── akshare/
│   │   ├── __init__.py
│   │   ├── akshare_provider.py     # ⭐ 重写
│   │   └── config.yaml
│   │
│   └── wind/                       # 新增Provider示例
│       ├── __init__.py
│       ├── wind_provider.py
│       └── config.yaml
│
├── utils/                      # 工具类（从Legacy迁移）
│   ├── __init__.py
│   ├── concurrent_executor.py  # ⭐ 多线程工具（迁移自FuturesWorker）
│   ├── progress_tracker.py     # ⭐ 进度跟踪（迁移）
│   └── data_mapper.py          # 字段映射工具（迁移）
│
├── config/                     # 配置
│   ├── providers/
│   │   ├── tushare.yaml
│   │   └── akshare.yaml
│   └── data_provider.yaml      # 全局配置
│
└── __init__.py
```

---

## 🔥 从Legacy迁移的有用部分

### 1. 多线程工具（FuturesWorker）

```python
# app/data_provider/utils/concurrent_executor.py

# ⭐ 从 utils/worker/multi_thread/futures_worker.py 迁移
# 保留完整的多线程功能

class ConcurrentExecutor:
    """并发执行器（从FuturesWorker迁移）"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
    
    async def execute(self, jobs: List[Dict], executor: Callable):
        """执行任务"""
        # 保留原有逻辑
        pass
```

### 2. 进度跟踪（ProgressTracker）

```python
# app/data_provider/utils/progress_tracker.py

# ⭐ 从 utils/progress/progress_tracker.py 迁移

class ProgressTracker:
    """进度跟踪器（迁移）"""
    
    def __init__(self, total: int):
        self.total = total
        self.completed = 0
    
    def update(self, count: int = 1):
        """更新进度"""
        self.completed += count
        progress = (self.completed / self.total) * 100
        logger.info(f"进度: {progress:.1f}%")
```

### 3. 字段映射工具

```python
# app/data_provider/utils/data_mapper.py

# ⭐ 从 BaseRenewer.map_api_data() 迁移

class DataMapper:
    """数据映射工具（迁移）"""
    
    def map(self, data, mapping: Dict):
        """映射字段"""
        # 保留原有的灵活映射逻辑
        pass
```

### 4. 增量更新逻辑

```python
# app/data_provider/utils/incremental_updater.py

# ⭐ 从 BaseRenewer.should_renew() 迁移

class IncrementalUpdater:
    """增量更新工具（迁移）"""
    
    def build_jobs(self, latest_market_open_day, db_records):
        """构建增量任务"""
        # 保留原有的智能增量逻辑
        # - 计算下一个周期
        # - 处理披露延迟
        # - 区分新股票和老股票
        pass
```

---

## 🎯 总结

### 你的观察完全正确！

| 问题 | 旧设计 | 新设计 |
|-----|--------|--------|
| **限流对象** | ❌ data_type级别 | ✅ API级别 |
| **多API协调** | ❌ 没考虑 | ✅ 智能并发 |
| **速率差异** | ❌ 不处理 | ✅ 自适应策略 |
| **架构** | ❌ 适配器包装Legacy | ✅ 全新重写 |

### 新设计的核心

1. **RateLimitRegistry**: API级别的限流注册表
2. **SmartConcurrentExecutor**: 智能处理多API并发
3. **自适应策略**: 根据限流差异选择串行/并行
4. **全新架构**: `app/data_provider/`，不依赖Legacy

### Legacy有用的部分会迁移

- ✅ 多线程工具（FuturesWorker）
- ✅ 进度跟踪（ProgressTracker）
- ✅ 字段映射（map_api_data逻辑）
- ✅ 增量更新（should_renew逻辑）
- ✅ 披露延迟处理
- ✅ Buffer机制

---

**这样的设计是否解决了你的担忧？**

最后更新: 2025-12-05  
维护者: @garnet

