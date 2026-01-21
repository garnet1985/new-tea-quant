"""
ApiJobScheduler: 多批 ApiJobBatch 的调度器。

职责：
- 针对多个 ApiJobBatch 进行调度和进度跟踪；
- 使用项目自己的 MultiThreadWorker 在批次级别做多线程；
- 对单个批次内部的执行委托给 ApiJobExecutor（负责拓扑排序 + 限流 + 并发执行）。
"""

from typing import Dict, Any, List

from loguru import logger

from core.modules.data_source.data_class.api_job_batch import ApiJobBatch
from core.modules.data_source.service.api_job_executor import ApiJobExecutor


class ApiJobScheduler:
    """
    ApiJob 批次调度器。

    输入：List[ApiJobBatch]
    输出：{batch_id: {job_id: result}}
    """

    def __init__(self, providers: Dict[str, Any], wait_buffer_seconds: float = 5.0):
        self.providers = providers or {}
        self.wait_buffer_seconds = wait_buffer_seconds

    async def run_batches(self, batches: List[ApiJobBatch]) -> Dict[str, Dict[str, Any]]:
        """
        调度执行多个 ApiJobBatch。
        """
        if not batches:
            return {}

        executor = ApiJobExecutor(providers=self.providers, wait_buffer_seconds=self.wait_buffer_seconds)

        # 单 batch：直接执行，不走多线程壳
        if len(batches) == 1:
            batch = batches[0]
            if not batch.api_jobs:
                return {batch.batch_id: {}}
            job_results = await executor.execute(batch.api_jobs)
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

        def _batch_executor(batch: ApiJobBatch) -> Dict[str, Any]:
            """
            单个批次的执行器（同步接口，供 MultiThreadWorker 使用）。
            """
            nonlocal completed_batches

            async def _run_single_batch():
                return await executor.execute(batch.api_jobs)

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

