"""
ApiJobExecutor: 单批 ApiJob 的执行器。

职责：
- 对一批 ApiJob（同一 data source 的一次执行计划）按依赖关系拓扑排序；
- 按阶段（stage）执行，每个 stage 内进行并发调用；
- 在调用前应用限流（RateLimiter），确保不超过配置的速率。

注意：
- 这里只关心“这一批 ApiJob 怎么跑完”，不关心多批之间如何调度；
- 多批之间的调度、进度等由更上层的 Scheduler 负责。
"""

from typing import Dict, Any, List

from loguru import logger

from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.service.rate_limiter import collect_api_limits, get_rate_limiter


class ApiJobExecutor:
    """
    单批 ApiJob 的执行器。

    输入：List[ApiJob]
    输出：{job_id: result}
    """

    def __init__(self, providers: Dict[str, Any], wait_buffer_seconds: float = 5.0):
        self.providers = providers or {}
        self.wait_buffer_seconds = wait_buffer_seconds

    async def execute(self, api_jobs: List[ApiJob]) -> Dict[str, Any]:
        """
        执行一批 ApiJobs。
        """
        if not api_jobs:
            return {}

        # 1. 拓扑排序：基于 depends_on 分阶段执行
        stages = self._topological_sort(api_jobs)

        # 2. 收集限流信息
        api_limits = collect_api_limits(api_jobs, self.providers)

        # 3. 决定 stage 内部的并发线程数
        workers = self._decide_workers(api_jobs, api_limits)

        # 4. 按阶段依次执行
        results: Dict[str, Any] = {}
        for stage in stages:
            if len(stage) == 1:
                job = stage[0]
                result = await self._execute_single_api_job(job, api_limits)
                results[job.job_id] = result
            else:
                stage_results = await self._execute_parallel(stage, workers, api_limits)
                results.update(stage_results)

        return results

    # ========== 拓扑排序 ==========

    def _topological_sort(self, api_jobs: List[ApiJob]) -> List[List[ApiJob]]:
        """
        拓扑排序，将 ApiJobs 分组为执行阶段。

        返回：
            List[List[ApiJob]]: 执行阶段列表，每个阶段内的 ApiJobs 可以并行执行。
        """
        from collections import defaultdict, deque

        job_map = {job.job_id: job for job in api_jobs}
        in_degree = {job.job_id: len(job.depends_on or []) for job in api_jobs}
        graph = defaultdict(list)

        for job in api_jobs:
            for dep_id in job.depends_on or []:
                if dep_id in job_map:
                    graph[dep_id].append(job.job_id)

        stages: List[List[ApiJob]] = []
        queue = deque([job_id for job_id, d in in_degree.items() if d == 0])

        while queue:
            current_stage: List[ApiJob] = []
            level_size = len(queue)
            for _ in range(level_size):
                job_id = queue.popleft()
                job = job_map[job_id]
                current_stage.append(job)

            stages.append(current_stage)

            for job in current_stage:
                for dependent_id in graph[job.job_id]:
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        queue.append(dependent_id)

        return stages

    # ========== 并发度决策 ==========

    def _decide_workers(self, api_jobs: List[ApiJob], api_limits: Dict[str, int]) -> int:
        """
        决定单批内部执行的并发度（线程/协程数量）。

        简化策略：
        - ApiJob 数量 <= 1：单线程；
        - 否则使用 2 作为小规模并发度（后续可根据限流信息调整）。
        """
        total_jobs = len(api_jobs)
        if total_jobs <= 1:
            return 1
        return 2

    # ========== 单个 Job 执行 ==========

    async def _execute_single_api_job(self, api_job: ApiJob, api_limits: Dict[str, int]) -> Any:
        """
        执行单个 ApiJob（应用限流）。
        """
        provider = self.providers.get(api_job.provider_name)
        if not provider:
            raise ValueError(f"Provider '{api_job.provider_name}' 未找到")

        # 应用限流：使用聚合后的限流值
        api_name = api_job.api_name or api_job.method
        job_limit = api_limits.get(api_job.job_id)
        if job_limit:
            limiter = get_rate_limiter(
                provider_name=api_job.provider_name,
                api_name=api_name,
                max_per_minute=job_limit,
                wait_buffer_seconds=self.wait_buffer_seconds,
            )
            import asyncio

            try:
                await asyncio.to_thread(limiter.acquire)
            except AttributeError:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, limiter.acquire)

        # 调用 Provider 方法
        method = getattr(provider, api_job.method, None)
        if not method:
            raise ValueError(f"Provider '{api_job.provider_name}' 没有方法 '{api_job.method}'")

        try:
            import asyncio

            if asyncio.iscoroutinefunction(method):
                result = await method(**(api_job.params or {}))
            else:
                result = method(**(api_job.params or {}))
            return result
        except Exception as e:
            logger.error(f"ApiJob {api_job.job_id} 执行失败: {e}")
            raise

    # ========== 阶段内并行执行 ==========

    async def _execute_parallel(
        self,
        api_jobs: List[ApiJob],
        workers: int,
        api_limits: Dict[str, int],
    ) -> Dict[str, Any]:
        """
        并行执行同一阶段内的多个 ApiJobs。
        """
        if len(api_jobs) == 1:
            job = api_jobs[0]
            result = await self._execute_single_api_job(job, api_limits)
            return {job.job_id: result}

        import asyncio

        tasks = [self._execute_single_api_job(job, api_limits) for job in api_jobs]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        results: Dict[str, Any] = {}
        for job, result in zip(api_jobs, results_list):
            if isinstance(result, Exception):
                logger.error(f"ApiJob {job.job_id} 执行失败: {result}")
                results[job.job_id] = None
            else:
                results[job.job_id] = result

        return results

