"""
Task 执行器

框架负责解析 Task 和 ApiJob Schema 并执行
"""
from typing import Dict, Any, List
from loguru import logger

from app.data_source.api_job import ApiJob, DataSourceTask


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
            rate_limiter: 限流器实例（可选，暂未实现）
        """
        self.providers = providers or {}
        self.rate_limiter = rate_limiter
    
    async def execute(self, tasks: List[DataSourceTask]) -> Dict[str, Dict[str, Any]]:
        """
        执行 Tasks
        
        流程：
        1. 展开 Tasks 为 ApiJobs
        2. 为每个 ApiJob 生成 job_id（如果未提供）
        3. 解析依赖关系（拓扑排序）
        4. 获取限流信息（从 Provider）
        5. 决定执行策略（线程数）
        6. 按阶段执行 ApiJobs
        7. 按 Task 分组收集结果
        8. 返回结果 {task_id: {job_id: result}}
        
        Args:
            tasks: Task 列表
        
        Returns:
            Dict[str, Dict[str, Any]]: {task_id: {job_id: result}} 字典
        """
        if not tasks:
            return {}
        
        # 1. 展开 Tasks 为 ApiJobs
        all_api_jobs = []
        task_job_mapping = {}  # {job_id: task_id} 映射
        
        for task in tasks:
            for api_job in task.api_jobs:
                all_api_jobs.append(api_job)
                task_job_mapping[api_job.job_id] = task.task_id
        
        # 2. 执行所有 ApiJobs（统一拓扑排序和执行）
        job_results = await self._execute_api_jobs(all_api_jobs)
        
        # 3. 按 Task 分组结果
        task_results = {}
        for job_id, result in job_results.items():
            task_id = task_job_mapping.get(job_id)
            if task_id:
                if task_id not in task_results:
                    task_results[task_id] = {}
                task_results[task_id][job_id] = result
        
        return task_results
    
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
    
    def _decide_workers(self, api_jobs: List[ApiJob], api_limits: Dict[str, int]) -> int:
        """
        决定线程数
        
        策略：
        1. 如果 ApiJob 数量 < 10，使用单线程
        2. 根据最严格的 API 限流计算最大并发数（限流的 80%）
        3. 线程数不超过 ApiJob 数量
        4. 应用最大/最小线程数限制
        """
        total_jobs = len(api_jobs)
        
        if total_jobs < 10:
            return 1
        
        if api_limits:
            # 取最严格的限流
            min_limit = min(api_limits.values())
            # 保守估计：使用限流的 80%
            max_concurrent = int(min_limit * 0.8)
        else:
            # 默认限流：60 次/分钟
            max_concurrent = 48  # 60 * 0.8
        
        # 线程数不超过 ApiJob 数量
        workers = min(max_concurrent, total_jobs)
        
        # 应用最大限制（最多 10 线程）
        workers = min(workers, 10)
        
        # 应用最小限制（至少 1 线程）
        workers = max(workers, 1)
        
        return workers
    
    async def _execute_single_api_job(self, api_job: ApiJob, api_limits: Dict[str, int]) -> Any:
        """执行单个 ApiJob"""
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
        
        # 应用限流
        if self.rate_limiter:
            await self.rate_limiter.acquire(api_job.api_name or api_job.method)
        
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
        并行执行多个 ApiJobs
        
        TODO: 实现多线程执行逻辑
        目前先串行执行，后续实现多线程
        """
        results = {}
        for api_job in api_jobs:
            result = await self._execute_single_api_job(api_job, api_limits)
            results[api_job.job_id] = result
        return results

