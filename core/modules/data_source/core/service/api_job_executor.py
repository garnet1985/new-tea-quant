"""
ApiJobExecutor: 单 bundle 内 ApiJob 拓扑执行 + 限流。

多 bundle 并发由 ``DataSourcePipelineRunner``（私有线程队列）负责。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from core.modules.data_source.core.data_class.api_job import ApiJob
from core.modules.data_source.core.service.rate_limiter import collect_api_limits, get_rate_limiter

logger = logging.getLogger(__name__)


class ApiJobExecutor:
    """执行一批 ApiJobs（同一 bundle 内）：拓扑分 stage、stage 内 asyncio 并发、限流。"""

    def __init__(self, providers: Dict[str, Any], wait_buffer_seconds: float = 5.0):
        self.providers = providers or {}
        self.wait_buffer_seconds = wait_buffer_seconds

    async def execute(self, api_jobs: List[ApiJob]) -> Dict[str, Any]:
        """执行一批 ApiJobs，返回 {job_id: result}。"""
        if not api_jobs:
            return {}

        stages = self._topological_sort(api_jobs)
        api_limits = collect_api_limits(api_jobs, self.providers)
        workers = self._decide_workers(api_jobs, api_limits)

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

    def _topological_sort(self, api_jobs: List[ApiJob]) -> List[List[ApiJob]]:
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
                current_stage.append(job_map[job_id])
            stages.append(current_stage)
            for job in current_stage:
                for dependent_id in graph[job.job_id]:
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        queue.append(dependent_id)

        return stages

    def _decide_workers(self, api_jobs: List[ApiJob], api_limits: Dict[str, int]) -> int:
        del api_limits
        if len(api_jobs) <= 1:
            return 1
        return 2

    async def _execute_single_api_job(self, api_job: ApiJob, api_limits: Dict[str, int]) -> Any:
        provider = self.providers.get(api_job.provider_name)
        if not provider:
            raise ValueError(f"Provider '{api_job.provider_name}' 未找到")

        api_name = api_job.api_name or api_job.method
        limiter_api_key = api_job.method or api_name
        job_id = api_job.job_id or api_name
        job_limit = api_limits.get(job_id) or api_limits.get(api_name) or 60
        provider_rate_limit = getattr(provider, "provider_rate_limit", None)

        limiter = get_rate_limiter(
            provider_name=api_job.provider_name,
            api_name=limiter_api_key,
            max_per_minute=job_limit,
            wait_buffer_seconds=self.wait_buffer_seconds,
            provider_rate_limit=provider_rate_limit,
        )
        limiter.acquire()

        method = getattr(provider, api_job.method, None)
        if not method:
            raise ValueError(
                f"Provider '{api_job.provider_name}' 没有方法 '{api_job.method}'"
            )

        try:
            if asyncio.iscoroutinefunction(method):
                return await method(**(api_job.params or {}))
            return method(**(api_job.params or {}))
        except Exception as e:
            logger.error("ApiJob %s 执行失败: %s", api_job.job_id, e)
            raise

    async def _execute_parallel(
        self,
        api_jobs: List[ApiJob],
        workers: int,
        api_limits: Dict[str, int],
    ) -> Dict[str, Any]:
        del workers
        if len(api_jobs) == 1:
            job = api_jobs[0]
            result = await self._execute_single_api_job(job, api_limits)
            return {job.job_id: result}

        tasks = [self._execute_single_api_job(job, api_limits) for job in api_jobs]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        results: Dict[str, Any] = {}
        for job, result in zip(api_jobs, results_list):
            if isinstance(result, Exception):
                logger.error("ApiJob %s 执行失败: %s", job.job_id, result)
                results[job.job_id] = None
            else:
                results[job.job_id] = result

        return results
