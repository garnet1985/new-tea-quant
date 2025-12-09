"""
Job 执行器

框架负责解析 Job Schema 并执行
"""
from typing import Dict, Any, List
from loguru import logger

from app.data_source.job import Job


class JobExecutor:
    """
    框架执行器
    
    职责：
    1. 解析 Job Schema（依赖关系、限流信息等）
    2. 决定执行策略（串行/并行、线程数、限流）
    3. 执行 Jobs
    4. 收集结果
    """
    
    def __init__(self, providers: Dict[str, Any] = None, rate_limiter=None):
        """
        初始化执行器
        
        Args:
            providers: Provider 实例字典 {provider_name: provider}
            rate_limiter: 限流器实例
        """
        self.providers = providers or {}
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
        
        Args:
            jobs: Job 列表
        
        Returns:
            Dict[str, Any]: {job_id: result} 字典
        """
        if not jobs:
            return {}
        
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
                job = stage[0]
                result = await self._execute_single_job(job, api_limits)
                results[job.job_id] = result
            else:
                # 多 Job，并行执行
                stage_results = await self._execute_parallel(stage, workers, api_limits)
                results.update(stage_results)
        
        return results
    
    def _assign_job_ids(self, jobs: List[Job]):
        """为每个 Job 生成 job_id（如果未提供）"""
        for i, job in enumerate(jobs):
            if job.job_id is None:
                job.job_id = f"job_{i}_{job.provider_name}_{job.method}"
    
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
        from collections import defaultdict, deque
        
        # 构建 Job 映射
        job_map = {job.job_id: job for job in jobs}
        
        # 构建依赖图
        in_degree = {job.job_id: len(job.depends_on) for job in jobs}
        graph = defaultdict(list)
        
        # 构建反向图（用于拓扑排序）
        for job in jobs:
            for dep_id in job.depends_on:
                if dep_id in job_map:
                    graph[dep_id].append(job.job_id)
        
        # Kahn 算法进行拓扑排序
        stages = []
        queue = deque([job_id for job_id, degree in in_degree.items() if degree == 0])
        
        while queue:
            # 当前阶段可以并行执行的 Jobs
            current_stage = []
            
            # 处理当前层级的所有节点
            level_size = len(queue)
            for _ in range(level_size):
                job_id = queue.popleft()
                job = job_map[job_id]
                current_stage.append(job)
            
            stages.append(current_stage)
            
            # 更新依赖计数，将新的可执行节点加入队列
            for job in current_stage:
                for dependent_id in graph[job.job_id]:
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        queue.append(dependent_id)
        
        return stages
    
    def _collect_api_limits(self, jobs: List[Job]) -> Dict[str, int]:
        """
        收集所有 Jobs 的限流信息
        
        从 Provider 的 api_limits 中获取
        """
        api_limits = {}
        
        for job in jobs:
            provider = self.providers.get(job.provider_name)
            if provider and hasattr(provider, 'get_api_limit'):
                limit = provider.get_api_limit(job.api_name)
                if limit:
                    api_limits[job.job_id] = limit
            else:
                # 默认限流：60 次/分钟
                api_limits[job.job_id] = 60
        
        return api_limits
    
    def _decide_workers(self, jobs: List[Job], api_limits: Dict[str, int]) -> int:
        """
        决定线程数
        
        策略：
        1. 如果 Job 数量 < 10，使用单线程
        2. 根据最严格的 API 限流计算最大并发数（限流的 80%）
        3. 线程数不超过 Job 数量
        4. 应用最大/最小线程数限制
        """
        total_jobs = len(jobs)
        
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
        
        # 线程数不超过 Job 数量
        workers = min(max_concurrent, total_jobs)
        
        # 应用最大限制（最多 10 线程）
        workers = min(workers, 10)
        
        # 应用最小限制（至少 1 线程）
        workers = max(workers, 1)
        
        return workers
    
    async def _execute_single_job(self, job: Job, api_limits: Dict[str, int]) -> Any:
        """执行单个 Job"""
        provider = self.providers.get(job.provider_name)
        if not provider:
            raise ValueError(f"Provider '{job.provider_name}' 未找到")
        
        # 应用限流
        if self.rate_limiter:
            await self.rate_limiter.acquire(job.api_name or job.method)
        
        # 调用 Provider 方法
        method = getattr(provider, job.method, None)
        if not method:
            raise ValueError(f"Provider '{job.provider_name}' 没有方法 '{job.method}'")
        
        try:
            # 调用方法（支持同步和异步）
            import asyncio
            if asyncio.iscoroutinefunction(method):
                result = await method(**job.params)
            else:
                result = method(**job.params)
            return result
        except Exception as e:
            logger.error(f"Job {job.job_id} 执行失败: {e}")
            raise
    
    async def _execute_parallel(
        self, 
        jobs: List[Job], 
        workers: int, 
        api_limits: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        并行执行多个 Jobs
        
        TODO: 实现多线程执行逻辑
        目前先串行执行，后续实现多线程
        """
        results = {}
        for job in jobs:
            result = await self._execute_single_job(job, api_limits)
            results[job.job_id] = result
        return results

