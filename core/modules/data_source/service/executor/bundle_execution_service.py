"""
BundleExecutionService - 负责对 ApiJob / ApiJobBundle 进行并发执行与结果汇总。

当前实现基本迁移自 BaseHandler._multi_thread_execute，行为保持一致，
只是将执行细节从 BaseHandler 中抽离出来，便于后续替换/扩展执行策略。
"""
from typing import Any, Dict, List, Tuple, Union, Callable
import logging

from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.data_class.api_job_bundle import ApiJobBundle
from core.modules.data_source.data_class.config import DataSourceConfig
from core.modules.data_source.service.api_job_executor import ApiJobExecutor
from core.modules.data_source.service.executor.bundle_progress import (
    AUTO_MAX_SAVE_BATCH_SIZE,
    BundleExecutionProgress,
    clear as clear_bundle_progress,
    current as current_bundle_progress,
    install as install_bundle_progress,
)
from core.modules.data_source.service.executor.save_batch_sizer import SaveBatchSizer


logger = logging.getLogger(__name__)

BundleSaveItem = Tuple[Any, Dict[str, Any]]


def _invoke_bundle_save(
    context: Dict[str, Any],
    batch_items: List[BundleSaveItem],
    save_mode: str,
    on_single_bundle_complete: Callable[[Dict[str, Any], Any, Dict[str, Any]], Any],
    on_batch_bundles_complete: Callable[[Dict[str, Any], List[BundleSaveItem]], Any],
) -> int:
    """
    batch：N 个 bundle 合并一次 on_batch_bundles_complete。
    immediate：逐 bundle 调用 on_single_bundle_complete。
    """
    if not batch_items:
        return 0
    if save_mode == "batch":
        on_batch_bundles_complete(context, batch_items)
        return len(batch_items)
    for job_bundle, fetched in batch_items:
        on_single_bundle_complete(context, job_bundle, fetched)
    return len(batch_items)


class BundleExecutionService:
    """
    执行一批 ApiJobBundle 的服务。

    约定：
    - 不直接依赖 BaseHandler，而是通过回调访问保存钩子。
    - save_mode=batch 时，每 save_batch_size 个 bundle（或 auto 动态阈值）触发 **一次** on_after_batch_bundles_complete。
    - save_mode=immediate 时，每个 bundle 触发 on_after_single_bundle_complete。
    """

    def execute(
        self,
        context: Dict[str, Any],
        jobs: List[Union[ApiJobBundle, ApiJob]],
        *,
        on_after_single_bundle_complete: Callable[[Dict[str, Any], Any, Dict[str, Any]], Any],
        on_after_batch_bundles_complete: Callable[[Dict[str, Any], List[BundleSaveItem]], Any],
        enrich_result_for_batch: Callable[[Dict[str, Any], ApiJobBundle, Dict[str, Any]], Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        执行 job bundles，并在合适的时机调用回调保存数据。

        Args:
            context: 执行上下文
            jobs: ApiJobBundle 或 ApiJob 列表
            on_after_single_bundle_complete: immediate 模式单 bundle 保存
            on_after_batch_bundles_complete: batch 模式多 bundle 合并保存
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
            """在同步/线程池上下文中运行 async coro（Python 3.9+ 线程内不用 get_event_loop）。"""
            import asyncio
            import concurrent.futures

            def _run_in_new_loop() -> Any:
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    return loop.run_until_complete(coro)
                finally:
                    try:
                        pending = asyncio.all_tasks(loop)
                        if pending:
                            loop.run_until_complete(
                                asyncio.gather(*pending, return_exceptions=True)
                            )
                    except Exception:
                        pass
                    try:
                        asyncio.set_event_loop(None)
                    except Exception:
                        pass
                    loop.close()

            has_running_loop = True
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                has_running_loop = False

            if not has_running_loop:
                return _run_in_new_loop()

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(_run_in_new_loop).result()

        # 仅一个 bundle：直接执行
        if len(bundles) == 1:
            bundle_id, apis, item = bundles[0]
            logger.debug("执行 1 个 bundle: bundle_id=%s", bundle_id)
            result = _run_async_in_sync(run_one_bundle(apis))
            logger.debug(
                "single_bundle 完成: bundle_id=%s, result_keys=%s",
                bundle_id,
                list(result.keys())[:5] if isinstance(result, dict) else "N/A",
            )

            # 获取 save_mode 配置
            config: DataSourceConfig = context.get("config")
            if not config:
                raise ValueError("config 必须配置 save_mode")
            save_mode = config.get_save_mode()

            # 根据 save_mode 决定是否调用保存钩子
            if save_mode != "unified":
                try:
                    _invoke_bundle_save(
                        context,
                        [(item, result)],
                        save_mode,
                        on_after_single_bundle_complete,
                        on_after_batch_bundles_complete,
                    )
                except Exception as e:
                    logger.error(
                        "single_bundle 保存失败: bundle_id=%s, error=%s",
                        bundle_id,
                        e,
                        exc_info=True,
                    )
            elif save_mode == "unified":
                logger.debug(
                    "single_bundle save_mode=unified，跳过 per-bundle 保存（统一在 _do_save）"
                )
            else:
                logger.debug("save_mode='unified' 或 item 非 ApiJobBundle，跳过 per-bundle 钩子")
            logger.debug("执行完成: 1/1 个 bundles")
            return result

        # 多个 bundle：使用多线程框架
        from core.infra.worker import (
            MultiThreadWorker,
            ThreadExecutionMode,
            ThreadJobStatus,
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
            execution_mode=ThreadExecutionMode.PARALLEL,
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
        bundle_progress = install_bundle_progress(
            context.get("data_source_key", "data_source"), total_bundles
        )

        # 启动进度监控线程
        import threading
        import time

        progress_stop = threading.Event()
        last_reported_done = 0
        PROGRESS_LOG_INTERVAL_SEC = 45
        PROGRESS_LOG_EVERY_N = 100
        last_progress_log_at = time.time()

        def _progress_monitor():
            """后台线程：定期输出抓取进度（INFO）。"""
            nonlocal last_reported_done, last_progress_log_at
            while not progress_stop.is_set():
                try:
                    stats = worker.get_stats()
                    bundle_progress.update_from_worker_stats(stats)
                    snap = bundle_progress.snapshot()
                    done = snap["done"]
                    now = time.time()

                    should_log = (
                        done >= last_reported_done + PROGRESS_LOG_EVERY_N
                        or (now - last_progress_log_at >= PROGRESS_LOG_INTERVAL_SEC and done > last_reported_done)
                        or (done >= total_bundles and done > last_reported_done)
                    )
                    if should_log and total_bundles > 0:
                        logger.info(bundle_progress.format_short())
                        last_reported_done = done
                        last_progress_log_at = now

                    if done >= total_bundles:
                        break
                except Exception:
                    pass
                time.sleep(2)

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

        # 根据配置决定批量保存大小（支持 save_batch_size: auto）
        config: DataSourceConfig = context.get("config")
        if not config:
            raise ValueError("config 必须配置 save_mode")
        save_mode = config.get_save_mode()
        save_batch_sizer = SaveBatchSizer(config, len(bundles), save_mode)

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
                            if job_bundle is not None and result.status == ThreadJobStatus.COMPLETED:
                                enriched = enrich_result_for_batch(context, job_bundle, result.result)
                                if enriched is not None:
                                    result.result = enriched

                            if result.status == ThreadJobStatus.COMPLETED and _has_actual_data(result.result):
                                pending_results.append(result)

                                if save_mode == "unified":
                                    processed_results.add(result.job_id)
                                    continue

                                batch_threshold = save_batch_sizer.current_size()
                                if len(pending_results) >= batch_threshold:
                                    batch = list(pending_results)
                                    pending_results.clear()
                                    for pr in batch:
                                        processed_results.add(pr.job_id)
                                    _batch_save_trigger_count[0] += 1
                                    save_batch_sizer.record_batch_start()

                                    def _run_batch_save(
                                        b=batch,
                                        bim=bundle_id_to_item,
                                    ):
                                        try:
                                            n = _invoke_bundle_save(
                                                context,
                                                [
                                                    (bim[pr.job_id], pr.result)
                                                    for pr in b
                                                    if pr.job_id in bim
                                                ],
                                                save_mode,
                                                on_after_single_bundle_complete,
                                                on_after_batch_bundles_complete,
                                            )
                                            logger.debug(
                                                "批量保存 %s bundles（%s 次写库调度）",
                                                len(b),
                                                1 if save_mode == "batch" and n else n,
                                            )
                                        except Exception as e:
                                            logger.error(
                                                "批量保存失败: %s",
                                                e,
                                                exc_info=True,
                                            )
                                        finally:
                                            save_batch_sizer.after_batch_saved(len(b), b)
                                            bundle_progress.add_saved(len(b))

                                    if batch_threshold == 1:
                                        _run_batch_save()
                                    else:
                                        batch_save_executor.submit(_run_batch_save)
                            elif result.status == ThreadJobStatus.FAILED:
                                processed_results.add(result.job_id)
                                error_msg = getattr(result, "error", None) or "未知错误"
                                logger.warning(f"⚠️ [批量保存] Bundle {result.job_id} 失败，跳过: {error_msg}")
                            elif result.status == ThreadJobStatus.COMPLETED:
                                processed_results.add(result.job_id)
                    time.sleep(0.5)
                except Exception as e:
                    logger.error(f"❌ [批量保存] 处理结果时出错: {e}", exc_info=True)
                    time.sleep(1)

        results_processing_thread = threading.Thread(target=_process_completed_results, daemon=True)
        results_processing_thread.start()

        logger.info(
            "[%s] 开始抓取，共 %s 个 bundle",
            bundle_progress.data_source_key,
            total_bundles,
        )

        try:
            worker.run_jobs()
        finally:
            progress_stop.set()
            results_processing_stop.set()
            progress_thread.join(timeout=2)
            results_processing_thread.join(timeout=2)
            bundle_progress.update_from_worker_stats(worker.get_stats())
            snap = bundle_progress.snapshot()
            if snap["failed"]:
                logger.warning(
                    "[%s] 抓取结束 %s/%s（%s%%），失败 %s",
                    bundle_progress.data_source_key,
                    snap["done"],
                    snap["total"],
                    snap["pct"],
                    snap["failed"],
                )
            else:
                logger.info(
                    "[%s] 抓取结束 %s/%s（%s%%）",
                    bundle_progress.data_source_key,
                    snap["done"],
                    snap["total"],
                    snap["pct"],
                )
            clear_bundle_progress()
            interrupted = getattr(worker, "_interrupted_by_signal", False)
            if interrupted:
                batch_save_executor.shutdown(wait=False)
                logger.warning("📋 [批量保存] 已收到中断信号，跳过等待 pending save，快速退出")
            else:
                batch_save_executor.shutdown(wait=True)
            logger.debug(
                "批量保存共触发 %s 次",
                _batch_save_trigger_count[0],
            )

        # 处理剩余结果
        results_list = worker.get_results()
        logger.debug(
            "multi_thread 剩余结果 %s 个（batch 保存已触发 %s 次）",
            len(results_list),
            _batch_save_trigger_count[0],
        )

        if pending_results and save_mode != "unified":
            tail_items: List[BundleSaveItem] = []
            tail_batch_results = []
            for pr in pending_results:
                if pr.job_id in processed_results:
                    continue
                processed_results.add(pr.job_id)
                if (
                    pr.status == ThreadJobStatus.COMPLETED
                    and _has_actual_data(pr.result)
                    and pr.job_id in bundle_id_to_item
                ):
                    tail_items.append((bundle_id_to_item[pr.job_id], pr.result))
                    tail_batch_results.append(pr)
            if tail_items:
                save_batch_sizer.record_batch_start()
                try:
                    _invoke_bundle_save(
                        context,
                        tail_items,
                        save_mode,
                        on_after_single_bundle_complete,
                        on_after_batch_bundles_complete,
                    )
                except Exception as e:
                    logger.error("批量保存最后一批失败: %s", e, exc_info=True)
                finally:
                    save_batch_sizer.after_batch_saved(
                        len(tail_batch_results), tail_batch_results
                    )
                    bundle_progress.add_saved(len(tail_batch_results))
            pending_results.clear()

        # 合并为 {job_id: result}
        merged: Dict[str, Any] = {}
        completed_count = len(processed_results)

        logger.debug(
            "multi_thread 处理剩余 %s 个结果（已处理 %s 个）",
            len(results_list),
            completed_count,
        )

        for r in results_list:
            if r.job_id in processed_results:
                continue

            job_bundle = bundle_id_to_item.get(r.job_id)
            if job_bundle is not None and r.status == ThreadJobStatus.COMPLETED:
                enriched = enrich_result_for_batch(context, job_bundle, r.result)
                if enriched is not None:
                    r.result = enriched

            if r.status == ThreadJobStatus.COMPLETED and _has_actual_data(r.result):
                merged.update(r.result)
                if save_mode != "unified" and r.job_id in bundle_id_to_item:
                    try:
                        _invoke_bundle_save(
                            context,
                            [(bundle_id_to_item[r.job_id], r.result)],
                            save_mode,
                            on_after_single_bundle_complete,
                            on_after_batch_bundles_complete,
                        )
                        processed_results.add(r.job_id)
                        completed_count += 1
                    except Exception as e:
                        logger.error(
                            "剩余结果保存失败: bundle_id=%s, error=%s",
                            r.job_id,
                            e,
                            exc_info=True,
                        )
                else:
                    processed_results.add(r.job_id)
                    completed_count += 1
            elif r.status == ThreadJobStatus.COMPLETED and not _has_actual_data(r.result):
                processed_results.add(r.job_id)
            elif r.status == ThreadJobStatus.FAILED and r.error:
                logger.warning(f"Bundle {r.job_id} 失败: {r.error}")
                completed_count += 1

        logger.debug(
            "执行完成: %s/%s 个 bundles",
            completed_count,
            total_bundles,
        )

        return merged

