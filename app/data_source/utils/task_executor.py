"""
Task 执行器

框架负责解析 Task 和 ApiJob Schema 并执行
"""
from typing import Dict, Any, List
from loguru import logger
import time
import threading

from app.data_source.api_job import ApiJob, DataSourceTask


class RateLimiter:
    """
    固定窗口限流器（不使用 buffer，直接使用注册的限流值）
    
    核心设计：
    1. 窗口起点对齐到分钟（自然分钟边界）
    2. sleep 不在锁里，使用条件变量通知等待线程
    3. 每个 (provider, api_name) 一个 limiter
    4. 并发线程只会阻塞自己，不会拖死别人
    """
    
    def __init__(self, max_per_minute: int, api_name: str = "default"):
        """
        初始化限流器
        
        Args:
            max_per_minute: 每分钟最大请求数（不使用 buffer）
            api_name: API 名称，用于日志
        """
        self.max_per_minute = max_per_minute
        self.api_name = api_name
        
        # 窗口对齐到自然分钟
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.window_start = self._current_window()
        self.count = 0
    
    def _current_window(self) -> int:
        """
        获取当前窗口的起始时间戳（对齐到自然分钟）
        
        Returns:
            当前分钟的开始时间戳（秒）
        """
        return int(time.time() // 60) * 60
    
    def acquire(self) -> None:
        """
        获取 API 调用许可
        
        如果达到限制，会等待直到下一个窗口（使用条件变量，不阻塞其他线程）
        """
        while True:
            now = time.time()
            current_window = self._current_window()
            
            with self.lock:
                # 新窗口：重置计数
                if current_window != self.window_start:
                    self.window_start = current_window
                    self.count = 0
                    # 通知所有等待的线程
                    self.condition.notify_all()
                
                # 如果还有配额，直接返回
                if self.count < self.max_per_minute:
                    self.count += 1
                    return  # 允许请求
                
                # 需要等待到下一个窗口
                next_window_start = self.window_start + 60
                sleep_time = next_window_start - now
                
                if sleep_time > 0:
                    # 使用条件变量等待，而不是 sleep
                    # 这样其他线程可以继续工作，只有这个线程等待
                    logger.debug(f"⏸️  {self.api_name} API: 当前窗口已调用 {self.count} 次（限制: {self.max_per_minute}/分钟），等待 {sleep_time:.1f} 秒到下一窗口...")
                    # 等待到下一个窗口开始，或者被通知（窗口重置时）
                    self.condition.wait(timeout=sleep_time)
                else:
                    # 如果 sleep_time <= 0，说明已经到下一个窗口了，继续循环
                    continue


class TaskExecutor:
    """
    框架执行器
    
    职责：
    1. 展开 Tasks 为 ApiJobs
    2. 解析 ApiJob Schema（依赖关系、限流信息等）
    3. 决定执行策略（串行/并行、线程数、限流）
    4. 执行 ApiJobs
    5. 按 Task 分组收集结果
    """
    
    def __init__(self, providers: Dict[str, Any] = None, rate_limiter=None):
        """
        初始化执行器
        
        Args:
            providers: Provider 实例字典 {provider_name: provider}（可选，默认从 ProviderInstancePool 获取）
            rate_limiter: 限流器实例（可选，如果为 None，会根据 API 限流自动创建）
        """
        self.providers = providers or {}
        self.rate_limiter = rate_limiter
        
        # 限流器缓存（按 api_name 缓存）
        self._rate_limiters: Dict[str, RateLimiter] = {}
        self._rate_limiters_lock = threading.Lock()
        
        # 用于增量保存的 handler 和 context（可选）
        self._handler = None
        self._handler_context = None
    
    def set_handler(self, handler, context: Dict[str, Any] = None):
        """
        设置 handler 和 context（用于增量保存）
        
        如果 handler 有 _save_single_task_result 方法，任务完成后会立即保存
        """
        self._handler = handler
        self._handler_context = context
    
    async def execute(self, tasks: List[DataSourceTask]) -> Dict[str, Dict[str, Any]]:
        """
        执行 Tasks（使用多线程，根据 task 数量自动分配线程数，最多10个）
        
        流程：
        1. 根据 task 数量决定线程数（最多10个）
        2. 使用 FuturesWorker 并行执行 tasks
        3. 每个 task 内部执行其所有 ApiJobs（处理依赖关系）
        4. 显示进度信息
        5. 返回结果 {task_id: {job_id: result}}
        
        Args:
            tasks: Task 列表
        
        Returns:
            Dict[str, Dict[str, Any]]: {task_id: {job_id: result}} 字典
        """
        if not tasks:
            return {}
        
        # 计算每个 task 的最小限流值（木桶效应）
        task_rate_limits = self._calculate_task_rate_limits(tasks)
        
        # 根据 task 数量决定线程数（最多10个）
        workers = self._decide_workers_by_task_count(len(tasks))
        
        # 根据最小限流值调整线程数（木桶效应：取所有 task 的最小限流值的最小值）
        if task_rate_limits:
            min_rate_limit = min(task_rate_limits.values())
            # 线程数不能超过限流值（每分钟请求数）
            # 保守估计：使用限流值的 80% 作为最大并发数
            max_workers_by_rate_limit = int(min_rate_limit * 0.8)
            workers = min(workers, max_workers_by_rate_limit)
            logger.info(f"📊 共 {len(tasks)} 个 Tasks，最小限流: {min_rate_limit}/分钟，使用 {workers} 个线程执行")
        else:
            logger.info(f"📊 共 {len(tasks)} 个 Tasks，使用 {workers} 个线程执行")
        
        # 如果只有1个 task，直接执行
        if len(tasks) == 1:
            task = tasks[0]
            task_result = await self._execute_single_task(task)
            return {task.task_id: task_result}
        
        # 多个 tasks，使用多线程执行
        from utils.worker.multi_thread.futures_worker import FuturesWorker, ExecutionMode
        import threading
        
        # 初始化进度计数器
        progress_lock = threading.Lock()
        completed_tasks = 0
        total_tasks = len(tasks)
        
        # 创建多线程工作器
        worker = FuturesWorker(
            max_workers=workers,
            execution_mode=ExecutionMode.PARALLEL,
            enable_monitoring=True,
            timeout=3600,  # 1小时超时
            is_verbose=False  # 禁用详细日志，我们自己控制进度显示
        )
        
        # 存储结果
        task_results = {}
        results_lock = threading.Lock()
        
        # 定义任务执行器（带进度显示）
        def task_executor(task: DataSourceTask) -> Dict[str, Any]:
            """执行单个 Task（同步函数，用于 FuturesWorker）"""
            import asyncio
            
            # 在事件循环中执行异步任务
            # 使用 nest_asyncio 来处理嵌套的事件循环
            try:
                import nest_asyncio
                nest_asyncio.apply()
            except ImportError:
                pass  # nest_asyncio 未安装，使用其他方法
            
            try:
                # 尝试获取当前事件循环
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行，创建新的事件循环
                    import concurrent.futures
                    import threading
                    future = concurrent.futures.Future()
                    
                    def _run():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            result = new_loop.run_until_complete(self._execute_single_task(task))
                            future.set_result(result)
                        except Exception as e:
                            future.set_exception(e)
                        finally:
                            new_loop.close()
                    
                    thread = threading.Thread(target=_run)
                    thread.start()
                    thread.join()
                    result = future.result()
                else:
                    # 如果事件循环没有运行，直接运行
                    result = loop.run_until_complete(self._execute_single_task(task))
            except RuntimeError:
                # 如果没有事件循环，创建新的
                result = asyncio.run(self._execute_single_task(task))
            
            # 保存结果
            with results_lock:
                task_results[task.task_id] = result
            
            # 如果 handler 支持增量保存，在任务完成的线程内立即保存（实现断点续传）
            if self._handler and hasattr(self._handler, '_save_single_task_result'):
                try:
                    import asyncio
                    # 在当前线程内直接保存（不需要额外线程）
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 如果事件循环正在运行，创建新的事件循环（在当前线程）
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            new_loop.run_until_complete(
                                self._handler._save_single_task_result(task.task_id, result, self._handler_context)
                            )
                        finally:
                            new_loop.close()
                    else:
                        loop.run_until_complete(
                            self._handler._save_single_task_result(task.task_id, result, self._handler_context)
                        )
                except Exception as e:
                    logger.error(f"❌ 增量保存任务 {task.task_id} 失败: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            # 更新进度
            with progress_lock:
                nonlocal completed_tasks
                completed_tasks += 1
                progress_percent = (completed_tasks / total_tasks) * 100
                
                # 尝试从 task 中提取股票信息（用于更友好的进度显示）
                stock_info = ""
                if task.api_jobs:
                    first_job = task.api_jobs[0]
                    stock_id = first_job.params.get("ts_code", "")
                    if stock_id:
                        stock_info = f" {stock_id}"
                
                logger.info(f"✅ Task{stock_info} 完成 - 进度: {progress_percent:.1f}% ({completed_tasks}/{total_tasks})")
            
            return result
        
        # 设置任务执行器
        worker.set_job_executor(task_executor)
        
        # 添加所有任务
        for task in tasks:
            worker.add_job(task.task_id, task)
        
        # 执行任务
        try:
            stats = worker.run_jobs()
            success_count = stats.get('completed_jobs', 0)
            failed_count = stats.get('failed_jobs', 0)
            
            if failed_count > 0:
                logger.warning(f"⚠️ 部分 Tasks 执行失败: {failed_count}/{total_tasks}")
            else:
                logger.info(f"✅ 所有 Tasks 执行完成: {success_count}/{total_tasks}")
        except Exception as e:
            logger.error(f"❌ 多线程执行失败: {e}")
            import traceback
            traceback.print_exc()
        
        return task_results
    
    async def _execute_single_task(self, task: DataSourceTask) -> Dict[str, Any]:
        """
        执行单个 Task（执行其所有 ApiJobs）
        
        处理依赖关系，按阶段执行 ApiJobs
        """
        # 执行该 task 的所有 ApiJobs
        api_jobs = task.api_jobs
        job_results = await self._execute_api_jobs(api_jobs)
        
        # 返回 {job_id: result} 字典
        return job_results
    
    def _calculate_task_rate_limits(self, tasks: List[DataSourceTask]) -> Dict[str, int]:
        """
        计算每个 task 的限流值（木桶效应：取该 task 所有 ApiJobs 的最小限流值）
        
        Args:
            tasks: Task 列表
            
        Returns:
            Dict[str, int]: {task_id: min_rate_limit} 字典
        """
        task_rate_limits = {}
        
        for task in tasks:
            # 收集该 task 所有 ApiJobs 的限流值
            api_limits = []
            
            for api_job in task.api_jobs:
                # 从 Provider 获取限流值
                provider = self.providers.get(api_job.provider_name)
                if not provider:
                    try:
                        from app.data_source.providers.provider_instance_pool import get_provider_pool
                        pool = get_provider_pool()
                        provider = pool.get_provider(api_job.provider_name)
                    except Exception:
                        pass
                
                if provider and hasattr(provider, 'get_api_limit'):
                    limit = provider.get_api_limit(api_job.api_name or api_job.method)
                    if limit:
                        api_limits.append(limit)
            
            # 木桶效应：取最小值
            if api_limits:
                task_rate_limits[task.task_id] = min(api_limits)
            else:
                # 如果没有限流信息，使用默认值（保守估计）
                task_rate_limits[task.task_id] = 200  # 默认 200 次/分钟
        
        return task_rate_limits
    
    def _decide_workers_by_task_count(self, task_count: int) -> int:
        """
        根据 task 数量决定线程数（最多10个）
        
        策略：
        1. 如果 task 数量 <= 1，使用单线程
        2. 如果 task 数量 <= 5，使用 2 线程
        3. 如果 task 数量 <= 10，使用 3 线程
        4. 如果 task 数量 <= 20，使用 5 线程
        5. 如果 task 数量 <= 50，使用 8 线程
        6. 否则使用 10 线程（最大）
        """
        if task_count <= 1:
            return 1
        elif task_count <= 5:
            return 2
        elif task_count <= 10:
            return 3
        elif task_count <= 20:
            return 5
        elif task_count <= 50:
            return 8
        else:
            return 10  # 最大10个线程
    
    async def _execute_api_jobs(self, api_jobs: List[ApiJob]) -> Dict[str, Any]:
        """
        执行 ApiJobs（内部方法）
        
        返回：
            Dict[str, Any]: {job_id: result} 字典
        """
        # 1. 拓扑排序
        stages = self._topological_sort(api_jobs)
        
        # 2. 获取限流信息
        api_limits = self._collect_api_limits(api_jobs)
        
        # 3. 决定线程数
        workers = self._decide_workers(api_jobs, api_limits)
        
        # 4. 按阶段执行
        results = {}
        for stage in stages:
            if len(stage) == 1:
                # 单 ApiJob，直接执行
                api_job = stage[0]
                result = await self._execute_single_api_job(api_job, api_limits)
                results[api_job.job_id] = result
            else:
                # 多 ApiJob，并行执行
                stage_results = await self._execute_parallel(stage, workers, api_limits)
                results.update(stage_results)
        
        return results
    
    def _topological_sort(self, api_jobs: List[ApiJob]) -> List[List[ApiJob]]:
        """
        拓扑排序，将 ApiJobs 分组为执行阶段
        
        返回：
            List[List[ApiJob]]: 执行阶段列表，每个阶段内的 ApiJobs 可以并行执行
        
        示例：
            ApiJobs: [A, B(depends_on=[A]), C(depends_on=[A]), D(depends_on=[B, C])]
            返回: [[A], [B, C], [D]]
                 阶段0    阶段1    阶段2
        """
        from collections import defaultdict, deque
        
        # 构建 ApiJob 映射
        job_map = {api_job.job_id: api_job for api_job in api_jobs}
        
        # 构建依赖图
        in_degree = {api_job.job_id: len(api_job.depends_on) for api_job in api_jobs}
        graph = defaultdict(list)
        
        # 构建反向图（用于拓扑排序）
        for api_job in api_jobs:
            for dep_id in api_job.depends_on:
                if dep_id in job_map:
                    graph[dep_id].append(api_job.job_id)
        
        # Kahn 算法进行拓扑排序
        stages = []
        queue = deque([job_id for job_id, degree in in_degree.items() if degree == 0])
        
        while queue:
            # 当前阶段可以并行执行的 ApiJobs
            current_stage = []
            
            # 处理当前层级的所有节点
            level_size = len(queue)
            for _ in range(level_size):
                job_id = queue.popleft()
                api_job = job_map[job_id]
                current_stage.append(api_job)
            
            stages.append(current_stage)
            
            # 更新依赖计数，将新的可执行节点加入队列
            for api_job in current_stage:
                for dependent_id in graph[api_job.job_id]:
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        queue.append(dependent_id)
        
        return stages
    
    def _collect_api_limits(self, api_jobs: List[ApiJob]) -> Dict[str, int]:
        """
        收集所有 ApiJobs 的限流信息
        
        从 Provider 的 api_limits 中获取
        """
        api_limits = {}
        
        for api_job in api_jobs:
            provider = self.providers.get(api_job.provider_name)
            if provider and hasattr(provider, 'get_api_limit'):
                limit = provider.get_api_limit(api_job.api_name)
                if limit:
                    api_limits[api_job.job_id] = limit
            else:
                # 默认限流：60 次/分钟
                api_limits[api_job.job_id] = 60
        
        return api_limits
    
    def _decide_workers(self, api_jobs: List[ApiJob], api_limits: Dict[str, int] = None) -> int:
        """
        决定线程数（用于单个 task 内部的 api_jobs 执行）
        
        策略：
        1. 如果 ApiJob 数量 <= 1，使用单线程
        2. 否则使用 2 线程（task 内部的小规模并行）
        """
        total_jobs = len(api_jobs)
        
        if total_jobs <= 1:
            return 1
        else:
            return 2  # task 内部使用少量线程
    
    def _get_rate_limiter(self, api_name: str, max_per_minute: int) -> RateLimiter:
        """
        获取或创建限流器（按 api_name 缓存）
        
        Args:
            api_name: API 名称
            max_per_minute: 每分钟最大请求数
            
        Returns:
            RateLimiter 实例
        """
        with self._rate_limiters_lock:
            if api_name not in self._rate_limiters:
                self._rate_limiters[api_name] = RateLimiter(max_per_minute, api_name)
            return self._rate_limiters[api_name]
    
    async def _execute_single_api_job(self, api_job: ApiJob, api_limits: Dict[str, int] = None) -> Any:
        """执行单个 ApiJob（应用限流）"""
        # 优先从 self.providers 获取，如果没有则从 ProviderInstancePool 获取
        provider = self.providers.get(api_job.provider_name)
        if not provider:
            try:
                from app.data_source.providers.provider_instance_pool import get_provider_pool
                pool = get_provider_pool()
                provider = pool.get_provider(api_job.provider_name)
            except Exception as e:
                logger.error(f"从 ProviderInstancePool 获取 Provider {api_job.provider_name} 失败: {e}")
        
        if not provider:
            raise ValueError(f"Provider '{api_job.provider_name}' 未找到")
        
        # 应用限流（不使用 buffer，直接使用注册的限流值）
        api_name = api_job.api_name or api_job.method
        if hasattr(provider, 'get_api_limit'):
            rate_limit = provider.get_api_limit(api_name)
            if rate_limit:
                # 获取或创建限流器
                limiter = self._get_rate_limiter(api_name, rate_limit)
                # 同步调用（限流器是同步的）
                limiter.acquire()
        
        # 调用 Provider 方法
        method = getattr(provider, api_job.method, None)
        if not method:
            raise ValueError(f"Provider '{api_job.provider_name}' 没有方法 '{api_job.method}'")
        
        try:
            # 调用方法（支持同步和异步）
            import asyncio
            if asyncio.iscoroutinefunction(method):
                result = await method(**api_job.params)
            else:
                result = method(**api_job.params)
            return result
        except Exception as e:
            logger.error(f"ApiJob {api_job.job_id} 执行失败: {e}")
            raise
    
    async def _execute_parallel(
        self, 
        api_jobs: List[ApiJob], 
        workers: int, 
        api_limits: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        并行执行多个 ApiJobs（用于单个 task 内部）
        
        使用 asyncio.gather 进行异步并行执行
        """
        if len(api_jobs) == 1:
            # 单个任务，直接执行
            api_job = api_jobs[0]
            result = await self._execute_single_api_job(api_job, api_limits)
            return {api_job.job_id: result}
        
        # 多个任务，使用 asyncio.gather 并行执行
        import asyncio
        
        # 创建任务列表
        tasks = [self._execute_single_api_job(api_job, api_limits) for api_job in api_jobs]
        
        # 并行执行
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 构建结果字典
        results = {}
        for api_job, result in zip(api_jobs, results_list):
            if isinstance(result, Exception):
                logger.error(f"ApiJob {api_job.job_id} 执行失败: {result}")
                results[api_job.job_id] = None
            else:
                results[api_job.job_id] = result
        
        return results

