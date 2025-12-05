# 多线程与限流机制

## 核心问题

新架构如何保留并增强现有的：
1. **多线程机制**（FuturesWorker）
2. **限流机制**（RateLimiter）
3. **进度跟踪**（ProgressTracker）

---

## 🎯 设计原则

### **适配器完全保留 Legacy 功能**

```
┌─────────────────────────────────────────┐
│         新架构（统一接口）                │
├─────────────────────────────────────────┤
│  Adapter（适配器）                       │
│  - 暴露统一接口                          │
│  - 委托给Legacy                          │
├─────────────────────────────────────────┤
│  Legacy（保留所有功能）⭐                │
│  - 多线程（FuturesWorker）               │
│  - 限流（RateLimiter）                   │
│  - 进度跟踪（ProgressTracker）           │
│  - 错误重试                              │
│  - 智能超时                              │
└─────────────────────────────────────────┘
```

**零功能损失！所有性能优化完全保留！**

---

## 📊 方案1：适配器透传（推荐）

### TushareAdapter 实现

```python
# app/data_source/v2/adapters/tushare_adapter.py

class TushareAdapter(BaseProvider):
    """
    Tushare 适配器
    
    ⭐ 完全保留Legacy的多线程和限流功能
    """
    
    def __init__(self, data_manager, is_verbose: bool = False):
        super().__init__(data_manager, is_verbose)
        
        # 创建Legacy实例（包含所有功能）
        self._legacy = LegacyTushare(
            connected_db=data_manager.db,
            is_verbose=is_verbose
        )
        
        # ✅ Legacy内部已包含：
        # - RateLimiterManager（限流管理器）
        # - ProgressTrackerManager（进度管理器）
        # - FuturesWorker（多线程工作器）
        # - 所有Renewers（含多线程配置）
    
    async def renew_all(self, end_date: str, context: ExecutionContext = None):
        """
        更新所有数据
        
        ⭐ 直接委托给Legacy，保留所有功能：
        - 多线程更新K线（4个worker）
        - 限流保护（200次/分钟）
        - 进度显示（实时进度百分比）
        - 错误重试（事务性原则）
        - 智能超时（30秒警告）
        """
        stock_list = context.stock_list if context else None
        
        # 直接调用Legacy的renew方法
        # ✅ 内部会：
        # 1. 用多线程更新K线（stock_kline_renewer配置了multithread）
        # 2. 用限流器保护API（每个renewer有独立的rate_limiter）
        # 3. 显示进度（"000001.SZ (平安银行) 更新完毕 - 进度: 3.3%"）
        return await self._legacy.renew(end_date, stock_list)
    
    async def renew_data_type(self, data_type: str, end_date: str, context: ExecutionContext = None):
        """
        更新指定数据类型
        
        ⭐ 映射到具体的Renewer，保留其多线程/限流配置
        """
        stock_list = context.stock_list if context else None
        
        # 映射到具体的Renewer
        if data_type == "stock_kline_daily":
            # ✅ stock_kline_renewer 配置：
            # - job_mode: multithread
            # - workers: 4
            # - rate_limit: 500/分钟
            # - 进度日志模板
            return self._legacy.stock_kline_renewer.renew(end_date, stock_list)
        
        elif data_type == "corporate_finance":
            # ✅ corporate_finance_renewer 配置：
            # - job_mode: multithread
            # - workers: 4
            # - rate_limit: 200/分钟
            return self._legacy.corporate_finance_renewer.renew(end_date, stock_list)
        
        elif data_type == "gdp":
            # ✅ gdp_renewer 配置：
            # - job_mode: simple（单线程，因为只有1个任务）
            # - rate_limit: 200/分钟
            return self._legacy.gdp_renewer.renew(end_date)
```

---

## 🔥 Legacy的多线程机制（完全保留）

### BaseRenewer 的多线程实现

```python
# app/data_source/providers/tushare/base_renewer.py

class BaseRenewer:
    """
    基础 Renewer
    
    ⭐ 内置完整的多线程和限流支持
    """
    
    def __init__(self, db, api, storage, config, is_verbose):
        self.config = config
        
        # === 多线程配置 ===
        self.multithread_config = config.get('multithread', {})
        self.workers = self.multithread_config.get('workers', 4)
        
        # === 限流器 ===
        rate_limit_config = config.get('rate_limit')
        if rate_limit_config:
            # 根据运行模式计算buffer
            if config.get('job_mode') == 'multithread':
                buffer = self.workers + 5  # ⭐ 多线程缓冲
            else:
                buffer = 5
            
            self.rate_limiter = APIRateLimiter(
                max_per_minute=rate_limit_config.get('max_per_minute', 200),
                api_name=config['table_name'],
                buffer=buffer
            )
    
    def renew(self, latest_market_open_day: str, stock_list: list = None):
        """主入口：根据配置选择执行模式"""
        jobs = self.should_renew(latest_market_open_day, stock_list)
        
        if len(jobs) > 0:
            if self.config['job_mode'].lower() == 'simple':
                return self._simple_renew(jobs)  # 单线程
            elif self.config['job_mode'].lower() == 'multithread':
                return self._multithread_renew(jobs)  # ⭐ 多线程
    
    def _multithread_renew(self, jobs: List[Dict]):
        """
        多线程更新
        
        ⭐ 完整功能：
        - 多线程并发（FuturesWorker）
        - 限流保护（rate_limiter）
        - 进度显示（progress bar）
        - 智能超时（execution_time监控）
        - 线程安全（thread_lock）
        """
        logger.info(f"🔄 开始多线程更新 {self.config['table_name']}")
        
        # 创建多线程工作器
        worker = FuturesWorker(
            max_workers=self.workers,  # ⭐ 4个线程
            execution_mode=ExecutionMode.PARALLEL,
            enable_monitoring=True,
            timeout=3600,
            is_verbose=False
        )
        
        # === 任务执行器（带进度和超时监控）===
        def job_executor_with_progress(job: Dict) -> bool:
            start_time = time.time()
            
            # 执行单个任务
            result = self._execute_single_job(job)
            
            execution_time = time.time() - start_time
            
            # 线程安全的进度显示
            with self._progress_lock:
                self._completed_jobs += 1
                progress_percent = (self._completed_jobs / self._total_jobs) * 100
                
                # ⭐ 智能超时监控
                if execution_time > 30:
                    logger.warning(f"任务执行时间过长: {execution_time:.1f}秒")
                
                # ⭐ 可配置的日志输出
                self.log_job_completion(job, result, progress_percent)
            
            return result
        
        # 初始化进度计数器（线程安全）
        import threading
        self._progress_lock = threading.Lock()
        self._completed_jobs = 0
        self._total_jobs = len(jobs)
        
        # 设置任务执行器
        worker.set_job_executor(job_executor_with_progress)
        
        # 添加所有任务
        for i, job in enumerate(jobs):
            worker.add_job(f"job_{i}", job)
        
        # ⭐ 执行（多线程）
        try:
            stats = worker.run_jobs()
            success_count = stats.get('completed_jobs', 0)
            total_count = stats.get('total_jobs', 0)
            
            logger.info(f"✅ {self.config['table_name']} 更新完毕")
            return success_count == total_count
        except Exception as e:
            logger.error(f"❌ 多线程执行失败: {e}")
            return False
    
    def _execute_single_job(self, job: Dict) -> bool:
        """
        执行单个任务
        
        ⭐ 关键：在这里应用限流
        """
        try:
            # === 限流保护 ===
            if self.rate_limiter:
                self.rate_limiter.acquire()  # ⭐ 阻塞直到获得令牌
            
            # 请求API
            api_results = self._request_apis(job)
            
            if api_results is None:
                return False  # API失败，任务失败
            
            if api_results == {}:
                return True  # 无数据（停牌），任务成功
            
            # 准备数据
            data = self.prepare_data_for_save(api_results, job)
            
            # 保存数据
            if data is not None:
                return self.save_data(data)
            
            return False
        except Exception as e:
            logger.error(f"❌ 任务执行失败: {e}")
            return False
```

---

## 🚦 限流机制（完全保留）

### APIRateLimiter 实现

```python
# app/data_source/providers/tushare/rate_limiter.py

class APIRateLimiter:
    """
    API限流器（令牌桶算法）
    
    ⭐ 线程安全的限流实现
    """
    
    def __init__(self, max_per_minute: int, api_name: str, buffer: int = 5):
        """
        Args:
            max_per_minute: 每分钟最大请求数
            api_name: API名称（用于日志）
            buffer: 缓冲区大小（多线程环境需要更大）
        """
        self.max_per_minute = max_per_minute
        self.api_name = api_name
        self.buffer = buffer
        
        # 令牌桶
        self.tokens = max_per_minute
        self.last_update = time.time()
        
        # 线程锁
        self._lock = threading.Lock()
        
        # 统计
        self._request_count = 0
        self._throttle_count = 0
    
    def acquire(self):
        """
        获取一个令牌（阻塞）
        
        ⭐ 线程安全，支持多线程并发调用
        """
        with self._lock:
            # 补充令牌
            now = time.time()
            elapsed = now - self.last_update
            
            if elapsed > 0:
                # 按时间补充令牌
                new_tokens = elapsed * (self.max_per_minute / 60.0)
                self.tokens = min(self.max_per_minute, self.tokens + new_tokens)
                self.last_update = now
            
            # 检查是否有令牌
            if self.tokens >= 1:
                self.tokens -= 1
                self._request_count += 1
                return
            
            # 没有令牌，需要等待
            wait_time = (1 - self.tokens) * (60.0 / self.max_per_minute)
            self._throttle_count += 1
            
            logger.warning(
                f"⏰ {self.api_name} 触发限流，等待 {wait_time:.2f}s "
                f"（已限流 {self._throttle_count} 次）"
            )
        
        # 释放锁后等待（避免阻塞其他线程）
        time.sleep(wait_time)
        
        # 递归获取令牌
        self.acquire()
```

### RateLimiterManager（管理多个限流器）

```python
# app/data_source/providers/tushare/rate_limiter.py

class RateLimiterManager:
    """
    限流器管理器
    
    ⭐ 管理多个独立的限流器
    """
    
    def __init__(self):
        self._limiters = {}
        self._lock = threading.Lock()
    
    def get_limiter(
        self, 
        api_name: str, 
        max_per_minute: int,
        buffer: int = 5
    ) -> APIRateLimiter:
        """
        获取或创建限流器
        
        每个API类型有独立的限流器
        """
        with self._lock:
            if api_name not in self._limiters:
                self._limiters[api_name] = APIRateLimiter(
                    max_per_minute=max_per_minute,
                    api_name=api_name,
                    buffer=buffer
                )
            
            return self._limiters[api_name]
```

---

## 🎯 Coordinator 层面的协调

### 问题：Provider之间的限流协调

```python
# 场景：Tushare和AKShare可能共享某些API限制
# 例如：都调用同一个底层服务

# 解决方案1：Provider内部管理（推荐）
# ✅ 每个Provider独立限流
# ✅ 简单，解耦
# ✅ 适合大多数场景

# 解决方案2：Coordinator协调（特殊场景）
# ⭐ 如果Provider之间需要协调限流
```

### Coordinator协调限流（可选）

```python
# app/data_source/v2/data_coordinator.py

class DataCoordinator:
    """
    数据协调器
    
    ⭐ 可选：协调Provider之间的限流
    """
    
    def __init__(self, registry, data_manager, config=None):
        self.registry = registry
        self.data_manager = data_manager
        self.config = config or {}
        
        # === 全局限流器（可选）===
        self._global_rate_limiter = None
        if self.config.get('enable_global_rate_limit'):
            self._global_rate_limiter = GlobalRateLimiter(
                max_per_minute=self.config.get('global_max_per_minute', 1000)
            )
    
    async def renew_all_providers(self, end_date: str):
        """
        更新所有Provider
        
        ⭐ 可选：在Provider之间应用全局限流
        """
        order = self.resolve_execution_order()
        
        for provider_name in order:
            provider = self.registry.get(provider_name)
            
            # === 全局限流（可选）===
            if self._global_rate_limiter:
                await self._global_rate_limiter.acquire_async()
            
            # 构建上下文
            context = await self._build_context(provider_name, end_date)
            
            # 执行更新（Provider内部还有自己的限流）
            try:
                await provider.renew_all(end_date, context)
            except Exception as e:
                logger.error(f"❌ {provider_name} 更新失败: {e}")
```

---

## 📊 配置示例

### Tushare配置（保留所有现有配置）

```python
# app/data_source/providers/tushare/renewers/stock_kline/config.py

CONFIG = {
    'table_name': 'stock_kline',
    'renew_mode': 'incremental',
    
    # === 多线程配置 ===
    'job_mode': 'multithread',  # ⭐ 启用多线程
    'multithread': {
        'workers': 4,  # ⭐ 4个线程
        'log': {
            'success': '{id} ({stock_name}) 更新完毕 - 进度: {progress}%',
            'failure': '{id} ({stock_name}) 更新失败'
        }
    },
    
    # === 限流配置 ===
    'rate_limit': {
        'max_per_minute': 500  # ⭐ 500次/分钟
    },
    
    # === API配置 ===
    'apis': [
        {
            'name': 'daily',
            'method': 'daily',
            'params': {
                'ts_code': '{ts_code}',
                'start_date': '{start_date}',
                'end_date': '{end_date}'
            },
            'mapping': {...}
        }
    ],
    
    # === 日期配置 ===
    'date': {
        'field': 'trade_date',
        'interval': 'day',
        'api_format': 'date'
    }
}
```

### 企业财务配置（不同的限流）

```python
# app/data_source/providers/tushare/renewers/corporate_finance/config.py

CONFIG = {
    'table_name': 'corporate_finance',
    'renew_mode': 'incremental',
    
    # === 多线程配置 ===
    'job_mode': 'multithread',
    'multithread': {
        'workers': 4  # 也是4个线程
    },
    
    # === 限流配置（更严格）===
    'rate_limit': {
        'max_per_minute': 200  # ⭐ 200次/分钟（比K线慢）
    },
    
    # === 日期配置（季度）===
    'date': {
        'field': 'quarter',
        'interval': 'quarter',
        'api_format': 'quarter',
        'disclosure_delay_months': 1  # ⭐ 披露延迟
    }
}
```

### GDP配置（单线程）

```python
# app/data_source/providers/tushare/renewers/gdp/config.py

CONFIG = {
    'table_name': 'gdp',
    'renew_mode': 'incremental',
    
    # === 单线程配置 ===
    'job_mode': 'simple',  # ⭐ 单线程（只有1个任务）
    
    # === 限流配置 ===
    'rate_limit': {
        'max_per_minute': 200
    },
    
    # === 日期配置（季度）===
    'date': {
        'field': 'quarter',
        'interval': 'quarter',
        'api_format': 'quarter'
    }
}
```

---

## 🚀 新Provider如何使用多线程和限流？

### 方案1：使用工具类（推荐）

```python
# app/data_source/v2/utils/concurrent_renewer.py

class ConcurrentRenewer:
    """
    通用的并发更新器
    
    ⭐ 提供给新Provider使用
    """
    
    def __init__(
        self,
        max_workers: int = 4,
        rate_limit: int = 200,
        api_name: str = "unknown"
    ):
        self.max_workers = max_workers
        
        # 创建限流器
        self.rate_limiter = APIRateLimiter(
            max_per_minute=rate_limit,
            api_name=api_name,
            buffer=max_workers + 5
        )
    
    async def renew_concurrent(
        self,
        jobs: List[Dict],
        job_executor: Callable
    ) -> bool:
        """
        并发执行任务
        
        Args:
            jobs: 任务列表
            job_executor: 任务执行函数
        """
        worker = FuturesWorker(
            max_workers=self.max_workers,
            execution_mode=ExecutionMode.PARALLEL
        )
        
        # 包装执行器（添加限流）
        def wrapped_executor(job):
            # 限流
            self.rate_limiter.acquire()
            # 执行
            return job_executor(job)
        
        worker.set_job_executor(wrapped_executor)
        
        for i, job in enumerate(jobs):
            worker.add_job(f"job_{i}", job)
        
        stats = worker.run_jobs()
        return stats.get('completed_jobs', 0) == stats.get('total_jobs', 0)

# 新Provider使用
class WindProvider(BaseProvider):
    def __init__(self, data_manager, is_verbose=False):
        super().__init__(data_manager, is_verbose)
        
        # ⭐ 使用工具类
        self.renewer = ConcurrentRenewer(
            max_workers=4,
            rate_limit=100,
            api_name='wind'
        )
    
    async def renew_all(self, end_date, context):
        stock_list = context.stock_list
        
        # 构建任务
        jobs = [{'ts_code': s, 'end_date': end_date} for s in stock_list]
        
        # 并发执行（自动限流）
        return await self.renewer.renew_concurrent(
            jobs,
            self._execute_single_job
        )
    
    def _execute_single_job(self, job):
        # 调用API
        # 保存数据
        pass
```

### 方案2：继承BaseRenewer（复用完整功能）

```python
# 如果新Provider的更新逻辑和Tushare类似
# 可以直接继承BaseRenewer

class WindRenewer(BaseRenewer):
    """Wind数据更新器"""
    
    def prepare_data_for_save(self, api_results, job):
        # 自定义数据处理
        pass

# Wind Provider使用
class WindProvider(BaseProvider):
    def __init__(self, data_manager, is_verbose=False):
        super().__init__(data_manager, is_verbose)
        
        # 创建Renewer（自带多线程和限流）
        self.news_renewer = WindRenewer(
            db=data_manager.db,
            api=self.wind_api,
            storage=self.wind_storage,
            config={
                'table_name': 'financial_news',
                'job_mode': 'multithread',
                'multithread': {'workers': 4},
                'rate_limit': {'max_per_minute': 100},
                # ...
            }
        )
    
    async def renew_all(self, end_date, context):
        # 直接调用Renewer
        return self.news_renewer.renew(end_date, context.stock_list)
```

---

## 📋 执行日志示例

### 多线程 + 限流的完整日志

```
🔄 开始更新所有Provider，截止日期: 20250101
📋 Provider执行顺序: tushare → akshare

▶️  更新 tushare...

  📋 更新股票列表...
  ✅ 股票列表更新完成，共 5234 只股票
  
  📈 更新股票K线数据...
  🔄 开始多线程更新 stock_kline，共 5234 个任务
  
  # ⭐ 多线程日志（4个线程并发）
  000001.SZ (平安银行) 更新完毕 - 进度: 0.1%
  000002.SZ (万科A) 更新完毕 - 进度: 0.2%
  000004.SZ (国华网安) 更新完毕 - 进度: 0.3%
  000005.SZ (世纪星源) 更新完毕 - 进度: 0.4%
  
  # ⭐ 限流警告（触发限流时）
  ⏰ stock_kline 触发限流，等待 1.2s（已限流 1 次）
  
  000006.SZ (深振业A) 更新完毕 - 进度: 0.5%
  000007.SZ (全新好) 更新完毕 - 进度: 0.6%
  ...
  
  # ⭐ 超时警告（某个股票特别慢）
  ⚠️  600000.SH (浦发银行) 执行时间过长: 35.2秒
  
  600000.SH (浦发银行) 更新完毕 - 进度: 99.8%
  600036.SH (招商银行) 更新完毕 - 进度: 99.9%
  601318.SH (中国平安) 更新完毕 - 进度: 100.0%
  
  ✅ stock_kline 更新完毕
  
  💼 更新企业财务数据...
  🔄 开始多线程更新 corporate_finance，共 5234 个任务
  
  # ⭐ 不同的限流配置（200次/分钟，比K线慢）
  ⏰ corporate_finance 触发限流，等待 2.5s（已限流 3 次）
  
  ...
  
✅ tushare 更新完成

▶️  更新 akshare...
  📊 开始更新复权因子，共 5234 只股票
  🔄 开始多线程更新 adj_factor，共 5234 个任务
  
  # ⭐ AKShare的限流（1000次/分钟，更快）
  000001.SZ 更新完毕 - 进度: 0.1%
  000002.SZ 更新完毕 - 进度: 0.2%
  ...
  
✅ akshare 更新完成

🎉 所有Provider更新完成
总耗时: 45分32秒
总请求数: 15702次
触发限流: 23次
```

---

## 🎯 总结

### 多线程机制

| 组件 | 功能 | 保留方式 |
|-----|------|---------|
| **FuturesWorker** | 多线程并发 | ✅ 通过适配器完全保留 |
| **进度跟踪** | 实时进度显示 | ✅ 完全保留 |
| **智能超时** | 超时监控 | ✅ 完全保留 |
| **线程安全** | 锁机制 | ✅ 完全保留 |

### 限流机制

| 组件 | 功能 | 保留方式 |
|-----|------|---------|
| **APIRateLimiter** | 令牌桶算法 | ✅ 完全保留 |
| **Buffer机制** | 多线程缓冲 | ✅ 完全保留 |
| **独立限流器** | 每个API独立 | ✅ 完全保留 |
| **限流警告** | 日志记录 | ✅ 完全保留 |

### 新Provider支持

| 方式 | 复杂度 | 推荐度 |
|-----|--------|--------|
| **继承BaseRenewer** | 低 | ⭐⭐⭐⭐⭐ |
| **使用工具类** | 中 | ⭐⭐⭐⭐ |
| **自己实现** | 高 | ⭐⭐ |

### 核心思想

```
适配器模式 = 统一接口 + 完整功能保留

新Provider = 复用工具类 or 继承BaseRenewer

零性能损失！
```

---

**最后更新**: 2025-12-05  
**维护者**: @garnet

