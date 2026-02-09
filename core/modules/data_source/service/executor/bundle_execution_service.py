"""
BundleExecutionService - 负责对 ApiJob / ApiJobBundle 进行并发执行与结果汇总。

当前实现基本迁移自 BaseHandler._multi_thread_execute，行为保持一致，
只是将执行细节从 BaseHandler 中抽离出来，便于后续替换/扩展执行策略。
"""
from typing import Any, Dict, List, Tuple, Union, Callable

from loguru import logger

from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.data_class.api_job_bundle import ApiJobBundle
from core.modules.data_source.data_class.config import DataSourceConfig
from core.modules.data_source.service.api_job_executor import ApiJobExecutor


class BundleExecutionService:
    """
    执行一批 ApiJobBundle 的服务。

    约定：
    - 不直接依赖 BaseHandler，而是通过回调访问 Hook（如 on_after_single_api_job_bundle_complete）。
    - save_mode / save_batch_size 等由 context.config 提供。
    """

    def execute(
        self,
        context: Dict[str, Any],
        jobs: List[Union[ApiJobBundle, ApiJob]],
        *,
        on_after_single_bundle_complete: Callable[[Dict[str, Any], ApiJobBundle, Dict[str, Any]], None],
        enrich_result_for_batch: Callable[[Dict[str, Any], ApiJobBundle, Dict[str, Any]], Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        执行 job bundles，并在合适的时机调用回调保存数据。

        Args:
            context: 执行上下文
            jobs: ApiJobBundle 或 ApiJob 列表
            on_after_single_bundle_complete: per-bundle 保存回调（由 Handler 提供）
            enrich_result_for_batch: 批量模式下增强 result 的回调（由 Handler 提供）

        Returns:
            Dict[str, Any]: 汇总后的 {job_id: result}
        """
        import asyncio

        # 归一化：统一成 (bundle_id, apis, item) 列表，便于后续按 bundle_id 回调钩子
        bundles: List[Tuple[str, List[ApiJob], Any]] = []
        data_source_key = context.get("data_source_key", "data_source")

        for i, item in enumerate(jobs or []):
            if isinstance(item, ApiJobBundle):
                bid = item.bundle_id or f"{data_source_key}_bundle_{i}"
                apis = item.apis or []
                bundles.append((bid, apis, item))
            elif isinstance(item, ApiJob):
                bid = getattr(item, "job_id", None) or f"{data_source_key}_job_{i}"
                bundles.append((bid, [item], item))
            else:
                logger.warning(f"未知 job 类型，已跳过: {type(item)}")
                continue

        if not bundles:
            return {}

        providers = context.get("providers") or {}
        executor = ApiJobExecutor(providers=providers)

        async def run_one_bundle(api_jobs: List[ApiJob]) -> Dict[str, Any]:
            if not api_jobs:
                return {}
            return await executor.execute(api_jobs)

        def _run_async_in_sync(coro):
            """在同步上下文中运行 async coro。若当前线程已有运行中的 loop 则在单独线程中起新 loop 执行。"""
            import concurrent.futures
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 当前线程已有运行中的 loop，在单独线程中执行
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        def _in_thread():
                            new_loop = asyncio.new_event_loop()
                            try:
                                asyncio.set_event_loop(new_loop)
                                return new_loop.run_until_complete(coro)
                            finally:
                                try:
                                    pending = asyncio.all_tasks(new_loop)
                                    if pending:
                                        new_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                                except Exception:
                                    pass
                                new_loop.close()
                        future = pool.submit(_in_thread)
                        return future.result()
                # 当前线程没有运行中的 loop，直接使用
                return loop.run_until_complete(coro)
            except RuntimeError:
                # 无法获取 event loop，创建新的
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    return loop.run_until_complete(coro)
                finally:
                    try:
                        pending = asyncio.all_tasks(loop)
                        if pending:
                            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    except Exception:
                        pass
                    loop.close()

        # 仅一个 bundle：直接执行
        if len(bundles) == 1:
            bundle_id, apis, item = bundles[0]
            logger.info(f"开始执行 1 个 bundle: bundle_id={bundle_id}")
            result = _run_async_in_sync(run_one_bundle(apis))
            logger.info(
                f"🔧 [single_bundle] 执行完成，准备调用钩子: bundle_id={bundle_id}, "
                f"result_keys={list(result.keys())[:5] if isinstance(result, dict) else 'N/A'}..."
            )

            # 获取 save_mode 配置
            config: DataSourceConfig = context.get("config")
            if not config:
                raise ValueError("config 必须配置 save_mode")
            save_mode = config.get_save_mode()

            # 根据 save_mode 决定是否调用钩子
            if save_mode != "unified" and isinstance(item, ApiJobBundle):
                try:
                    logger.info(f"🔧 [single_bundle] 调用 on_after_single_api_job_bundle_complete: bundle_id={bundle_id}")
                    on_after_single_bundle_complete(context, item, result)
                    logger.info(f"✅ [single_bundle] on_after_single_api_job_bundle_complete 调用成功: bundle_id={bundle_id}")
                except Exception as e:
                    logger.error(
                        f"❌ [single_bundle] on_after_single_api_job_bundle_complete 调用失败: "
                        f"bundle_id={bundle_id}, error={e}",
                        exc_info=True,
                    )
            elif save_mode == "unified":
                logger.debug(
                    "🔧 [single_bundle] save_mode='unified'，跳过 on_after_single_api_job_bundle_complete"
                    "（将在 _do_save 中统一保存）"
                )
            else:
                logger.debug("save_mode='unified' 或 item 非 ApiJobBundle，跳过 per-bundle 钩子")
            logger.info("执行完成: 1/1 个 bundles")
            return result

        # 多个 bundle：使用多线程框架
        from core.infra.worker.multi_thread.futures_worker import (
            MultiThreadWorker,
            ExecutionMode,
            JobStatus,
        )

        def _decide_workers(bundle_count: int) -> int:
            if bundle_count <= 1:
                return 1
            if bundle_count <= 5:
                return 2
            if bundle_count <= 10:
                return 3
            if bundle_count <= 20:
                return 5
            if bundle_count <= 50:
                return 8
            return 10

        max_workers = _decide_workers(len(bundles))

        def _bundle_executor(api_jobs: List[ApiJob]) -> Dict[str, Any]:
            """单个 bundle 的执行器（同步接口，供 MultiThreadWorker 调用）。job_data 即 apis 列表。"""
            return _run_async_in_sync(run_one_bundle(api_jobs))

        worker = MultiThreadWorker(
            max_workers=max_workers,
            execution_mode=ExecutionMode.PARALLEL,
            job_executor=_bundle_executor,
            enable_monitoring=True,
            timeout=3600,
            is_verbose=False,
        )

        bundle_id_to_item: Dict[str, Any] = {}
        for bundle_id, apis, item in bundles:
            worker.add_job(bundle_id, apis)
            bundle_id_to_item[bundle_id] = item

        total_bundles = len(bundles)

        # 启动进度监控线程
        import threading
        import time

        progress_stop = threading.Event()
        last_reported_count = 0
        PROGRESS_INTERVAL = 50  # 每完成50个job输出一次进度

        def _progress_monitor():
            """后台线程：定期输出进度"""
            nonlocal last_reported_count
            while not progress_stop.is_set():
                try:
                    stats = worker.get_stats()
                    completed = stats.get("completed_jobs", 0) + stats.get("failed_jobs", 0)

                    if completed >= last_reported_count + PROGRESS_INTERVAL:
                        current_percent = int((completed / total_bundles * 100)) if total_bundles > 0 else 0
                        ds_key = context.get("data_source_key")
                        logger.info(f"📊 [{ds_key}] 进度: {completed}/{total_bundles} ({current_percent}%)")
                        last_reported_count = (completed // PROGRESS_INTERVAL) * PROGRESS_INTERVAL

                    if completed >= total_bundles:
                        if completed > last_reported_count:
                            current_percent = int((completed / total_bundles * 100)) if total_bundles > 0 else 0
                            ds_key = context.get("data_source_key")
                            logger.info(f"📊 [{ds_key}] 进度: {completed}/{total_bundles} ({current_percent}%)")
                        break
                except Exception:
                    pass
                time.sleep(1)

        progress_thread = threading.Thread(target=_progress_monitor, daemon=True)
        progress_thread.start()

        # 等待一小段时间，确保进度监控线程启动
        time.sleep(0.1)

        # 批量处理完成的结果：启动一个线程定期从 results_queue 中取出结果并批量调用钩子
        processed_results = set()  # 记录已处理的结果，避免重复处理
        pending_results = []  # 待处理的结果列表
        results_processing_stop = threading.Event()
        import concurrent.futures

        batch_save_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        context["_batch_save_executor"] = batch_save_executor  # batch 模式时异步执行 _run_batch_save

        # 根据配置决定批量保存大小
        config: DataSourceConfig = context.get("config")
        if not config:
            raise ValueError("config 必须配置 save_mode")
        save_mode = config.get_save_mode()
        if save_mode == "immediate":
            BATCH_SAVE_SIZE = 1  # 立即保存：每个 bundle 完成后立即保存
        elif save_mode == "batch":
            BATCH_SAVE_SIZE = config.get_save_batch_size() if config else 50
        else:  # unified
            BATCH_SAVE_SIZE = float("inf")  # 统一保存：不在这里保存，在 _do_save 中统一保存

        def _has_actual_data(result_dict: Dict[str, Any]) -> bool:
            """
            检查结果字典是否真正包含数据。

            result_dict 的格式是 {job_id: result_data}，其中 result_data 可能是：
            - None: 执行失败
            - []: 空列表（API返回空数据）
            - [data]: 有数据的列表
            - DataFrame: pandas DataFrame
            """
            if not isinstance(result_dict, dict) or not result_dict:
                return False

            import pandas as pd

            for job_id, result_data in result_dict.items():
                if result_data is None:
                    continue
                if isinstance(result_data, pd.DataFrame):
                    if not result_data.empty:
                        return True
                elif isinstance(result_data, (list, tuple)):
                    if len(result_data) > 0:
                        return True
                elif result_data:
                    return True
            return False

        _batch_save_trigger_count = [0]

        def _process_completed_results():
            """批量处理完成的结果：根据 save_mode 决定保存时机。"""
            from queue import Empty

            while not results_processing_stop.is_set() or worker.is_running:
                try:
                    stats = worker.get_stats()
                    results_count = stats.get("results_count", 0)

                    if results_count > 0:
                        available_results = worker.get_results()
                        for result in available_results:
                            if result.job_id in processed_results:
                                continue

                            job_bundle = bundle_id_to_item.get(result.job_id)
                            if job_bundle is not None and result.status == JobStatus.COMPLETED:
                                enriched = enrich_result_for_batch(context, job_bundle, result.result)
                                if enriched is not None:
                                    result.result = enriched

                            if result.status == JobStatus.COMPLETED and _has_actual_data(result.result):
                                pending_results.append(result)

                                if save_mode == "unified":
                                    processed_results.add(result.job_id)
                                    continue

                                if len(pending_results) >= BATCH_SAVE_SIZE:
                                    batch = list(pending_results)
                                    pending_results.clear()
                                    for pr in batch:
                                        processed_results.add(pr.job_id)
                                    _batch_save_trigger_count[0] += 1

                                    def _run_batch_save(b=batch, bim=bundle_id_to_item):
                                        saved = 0
                                        for pr in b:
                                            if pr.job_id in bim:
                                                try:
                                                    on_after_single_bundle_complete(context, bim[pr.job_id], pr.result)
                                                    saved += 1
                                                except Exception as e:
                                                    logger.error(
                                                        "❌ [批量保存] on_after_single_api_job_bundle_complete 调用失败: "
                                                        f"bundle_id={pr.job_id}, error={e}",
                                                        exc_info=True,
                                                    )
                                        logger.info(f"✅ [批量保存] 完成 {saved}/{len(b)} 个 bundles 的保存")

                                    if BATCH_SAVE_SIZE == 1:
                                        _run_batch_save()
                                    else:
                                        batch_save_executor.submit(_run_batch_save)
                            elif result.status == JobStatus.FAILED:
                                processed_results.add(result.job_id)
                                error_msg = getattr(result, "error", None) or "未知错误"
                                logger.warning(f"⚠️ [批量保存] Bundle {result.job_id} 失败，跳过: {error_msg}")
                            elif result.status == JobStatus.COMPLETED:
                                processed_results.add(result.job_id)
                    time.sleep(0.5)
                except Exception as e:
                    logger.error(f"❌ [批量保存] 处理结果时出错: {e}", exc_info=True)
                    time.sleep(1)

        results_processing_thread = threading.Thread(target=_process_completed_results, daemon=True)
        results_processing_thread.start()

        try:
            worker.run_jobs()
        finally:
            progress_stop.set()
            results_processing_stop.set()
            progress_thread.join(timeout=2)
            results_processing_thread.join(timeout=2)
            interrupted = getattr(worker, "_interrupted_by_signal", False)
            if interrupted:
                batch_save_executor.shutdown(wait=False)
                logger.warning("📋 [批量保存] 已收到中断信号，跳过等待 pending save，快速退出")
            else:
                batch_save_executor.shutdown(wait=True)
            logger.info(f"📋 [批量保存] 处理线程期间共触发 {_batch_save_trigger_count[0]} 次 batch 保存")

        # 处理剩余结果
        results_list = worker.get_results()
        logger.info(
            f"🔧 [multi_thread] worker.run_jobs() 完成，获取到 {len(results_list)} 个剩余结果"
            f"（处理线程已触发 {_batch_save_trigger_count[0]} 次 batch 保存）"
        )

        if pending_results and save_mode != "unified":
            logger.info(f"🔧 [批量保存] 处理最后一批 {len(pending_results)} 个有数据的结果...")
            saved_count = 0
            for pending_result in pending_results:
                if pending_result.job_id in processed_results:
                    continue

                processed_results.add(pending_result.job_id)

                if pending_result.status == JobStatus.COMPLETED and _has_actual_data(pending_result.result):
                    if pending_result.job_id in bundle_id_to_item:
                        try:
                            on_after_single_bundle_complete(
                                context, bundle_id_to_item[pending_result.job_id], pending_result.result
                            )
                            saved_count += 1
                        except Exception as e:
                            logger.error(
                                "❌ [批量保存] on_after_single_api_job_bundle_complete 调用失败: "
                                f"bundle_id={pending_result.job_id}, error={e}",
                                exc_info=True,
                            )
            logger.info(f"✅ [批量保存] 完成最后一批 {saved_count}/{len(pending_results)} 个 bundles 的保存")
            pending_results.clear()

        # 合并为 {job_id: result}
        merged: Dict[str, Any] = {}
        completed_count = len(processed_results)

        logger.info(f"🔧 [multi_thread] 开始处理 {len(results_list)} 个剩余结果（已批量处理 {completed_count} 个）")

        for r in results_list:
            if r.job_id in processed_results:
                continue

            job_bundle = bundle_id_to_item.get(r.job_id)
            if job_bundle is not None and r.status == JobStatus.COMPLETED:
                enriched = enrich_result_for_batch(context, job_bundle, r.result)
                if enriched is not None:
                    r.result = enriched

            if r.status == JobStatus.COMPLETED and _has_actual_data(r.result):
                merged.update(r.result)
                if save_mode != "unified" and r.job_id in bundle_id_to_item:
                    try:
                        on_after_single_bundle_complete(context, bundle_id_to_item[r.job_id], r.result)
                        processed_results.add(r.job_id)
                        completed_count += 1
                    except Exception as e:
                        logger.error(
                            "❌ [剩余结果] on_after_single_api_job_bundle_complete 调用失败: "
                            f"bundle_id={r.job_id}, error={e}",
                            exc_info=True,
                        )
                else:
                    processed_results.add(r.job_id)
                    completed_count += 1
            elif r.status == JobStatus.COMPLETED and not _has_actual_data(r.result):
                processed_results.add(r.job_id)
            elif r.status == JobStatus.FAILED and r.error:
                logger.warning(f"Bundle {r.job_id} 失败: {r.error}")
                completed_count += 1

        logger.info(f"执行完成: {completed_count}/{total_bundles} 个 bundles（批量处理 {len(processed_results)} 个）")

        return merged

