"""
ApiJobExecutor: ApiJob 执行器（合并了原 ApiJobScheduler 的功能）。

职责：
- 对一批 ApiJob 按依赖关系拓扑排序、限流、并发执行；
- 支持多批次调度（使用 MultiThreadWorker 并行执行多个批次）；
- 在调用前应用限流（RateLimiter），确保不超过配置的速率。
"""

from typing import Dict, Any, List

from loguru import logger

from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.data_class.api_job_bundle import ApiJobBundle
from core.modules.data_source.service.rate_limiter import collect_api_limits, get_rate_limiter


class ApiJobExecutor:
    """
    ApiJob 执行器（支持单批次和多批次）。

    单批次：
    输入：List[ApiJob] 或 ApiJobBundle
    输出：{job_id: result}

    多批次：
    输入：List[ApiJobBundle]
    输出：{batch_id: {job_id: result}}
    """

    def __init__(self, providers: Dict[str, Any], wait_buffer_seconds: float = 5.0):
        self.providers = providers or {}
        self.wait_buffer_seconds = wait_buffer_seconds

    async def run_batches(self, batches: List[ApiJobBundle]) -> Dict[str, Dict[str, Any]]:
        """
        调度执行多个 ApiJobBatch（原 ApiJobScheduler 的功能）。
        
        Args:
            batches: ApiJobBatch 列表
            
        Returns:
            Dict[str, Dict[str, Any]]: {batch_id: {job_id: result}}
        """
        if not batches:
            return {}

        # 单 batch：直接执行
        if len(batches) == 1:
            batch = batches[0]
            if not batch.api_jobs:
                return {batch.batch_id: {}}
            job_results = await self.execute(batch.api_jobs)
            return {batch.batch_id: job_results}

        # 多个 batch：使用 MultiThreadWorker 并行调度
        from core.infra.worker.multi_thread.futures_worker import MultiThreadWorker, ExecutionMode
        import threading
        import asyncio

        total_batches = len(batches)
        completed_batches = 0
        progress_lock = threading.Lock()

        def _decide_workers(batch_count: int) -> int:
            if batch_count <= 1:
                return 1
            elif batch_count <= 5:
                return 2
            elif batch_count <= 10:
                return 3
            elif batch_count <= 20:
                return 5
            elif batch_count <= 50:
                return 8
            else:
                return 10

        workers = _decide_workers(total_batches)

        worker = MultiThreadWorker(
            max_workers=workers,
            execution_mode=ExecutionMode.PARALLEL,
            enable_monitoring=True,
            timeout=3600,
            is_verbose=False,
        )

        results_by_batch: Dict[str, Dict[str, Any]] = {}
        results_lock = threading.Lock()

        def _batch_executor(batch: ApiJobBundle) -> Dict[str, Any]:
            """
            单个批次的执行器（同步接口，供 MultiThreadWorker 使用）。
            """
            nonlocal completed_batches

            async def _run_single_batch():
                return await self.execute(batch.api_jobs)

            result: Dict[str, Any] = {}

            # 在线程中运行异步执行（适配 MultiThreadWorker 的同步接口）
            try:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        new_loop = asyncio.new_event_loop()
                        try:
                            asyncio.set_event_loop(new_loop)
                            result = new_loop.run_until_complete(_run_single_batch())
                        finally:
                            new_loop.close()
                    else:
                        result = loop.run_until_complete(_run_single_batch())
                except RuntimeError:
                    result = asyncio.run(_run_single_batch())
            finally:
                # 写入结果
                with results_lock:
                    results_by_batch[batch.batch_id] = result

                # 更新进度
                with progress_lock:
                    completed_batches += 1
                    progress = completed_batches / total_batches * 100
                    logger.info(
                        f"✅ ApiJobBatch {batch.batch_id} 完成 - 进度: "
                        f"{progress:.1f}% ({completed_batches}/{total_batches})"
                    )

            return result

        # 设置 job 执行函数
        worker.set_job_executor(_batch_executor)

        # 添加所有批次
        for batch in batches:
            if not batch.api_jobs:
                logger.warning(f"ApiJobBatch {batch.batch_id} 没有 api_jobs，已跳过")
                continue
            worker.add_job(batch.batch_id, batch)

        # 执行所有批次
        try:
            stats = worker.run_jobs()
            completed = stats.get("completed_jobs", 0)
            failed = stats.get("failed_jobs", 0)
            not_done = stats.get("not_done_count", 0)

            if failed == 0 and not_done == 0 and completed == total_batches:
                logger.info(f"✅ 所有 ApiJobBatch 执行完成: {completed}/{total_batches}")
            else:
                logger.warning(
                    f"⚠️ ApiJobBatch 执行结束: 成功 {completed}/{total_batches}, "
                    f"失败 {failed}, 未完成 {not_done}"
                )
        except Exception as e:
            logger.error(f"❌ 多线程执行 ApiJobBatch 失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

        return results_by_batch

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
