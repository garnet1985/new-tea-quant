from typing import Any, Dict, List, Tuple, Optional, Union

from loguru import logger

from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper
from core.modules.data_source.service.api_job_executor import ApiJobExecutor
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.data_class.api_job_bundle import ApiJobBundle
from core.modules.data_source.data_class.config import DataSourceConfig
from core.modules.data_source.renew_manager import RenewManager
from core.global_enums.enums import UpdateMode
from core.modules.data_manager.data_manager import DataManager
from core.infra.project_context.config_manager import ConfigManager


class BaseHandler:
    """
    Base Handler class
    """
    def __init__(self,
        data_source_key: str,
        schema: Any,
        config: DataSourceConfig,
        providers: Dict[str, BaseProvider],
        depend_on_data_source_names: List[str] = None,
    ):
        if depend_on_data_source_names is None:
            depend_on_data_source_names = []
        self.context = {
            "data_source_key": data_source_key,
            "schema": schema,
            "config": config,
            "providers": providers,
            "data_manager": DataManager.get_instance(),
            "depend_on_data_source_names": depend_on_data_source_names
        }

    # ================================
    # Getters
    # ================================

    def get_key(self) -> Optional[str]:
        """数据源配置键（mapping 中的 key，用于串联 config、dependencies 等），与 DB 表名无关。"""
        return self.context.get("data_source_key")

    def get_dependency_data_source_names(self) -> List[str]:
        """获取依赖的数据源名称列表"""
        return self.context.get("depend_on_data_source_names", [])

    # ================================
    # Main entrance: execute
    # ================================
    def execute(self, dependencies_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handler 的同步执行入口（默认实现）。

        流程大纲：
        0. on_before_run：若返回非 None，直接作为 result 返回，跳过后续所有步骤；
        1. _preprocess：预处理阶段（构建 ApiJobs、计算日期范围、调用 on_before_fetch 钩子）；
        2. _executing：执行阶段（构建批次、执行 API 请求、调用 on_after_fetch 钩子）；
        3. _postprocess：后处理阶段（标准化数据、调用 on_after_normalize 钩子、数据验证）；
        4. _do_save：非 is_dry_run 时先调用 on_before_save（用户可返回替代数据），再系统写入绑定表；
        5. 返回标准化后的数据。
        """
        self._inject_dependencies(dependencies_data)
        config = self.context.get("config")
        self.context["is_dry_run"] = bool(config.get("is_dry_run", False) if config else False)

        early_result = self.on_before_run(self.context)
        if early_result is not None:
            return early_result

        jobs = self._preprocess(dependencies_data)

        fetched_data = self._executing(jobs)

        normalized_data = self._postprocess(fetched_data)

        normalized_data = self._do_save(normalized_data)

        return normalized_data
    

    # ================================
    # Preprocess stage
    # ================================
    # 请注意dependencies是只读的，修改可能会导致全局错误，请不要修改dependencies的值
    def _preprocess(self, dependencies_data: Optional[Dict[str, Any]] = None) -> List[ApiJob]:
        """
        预处理阶段：在执行 API 请求前的所有准备工作。
        依赖与 is_dry_run 已由 execute() 在调用本方法前注入 context。
        
        步骤：
        1. 调用 on_prepare_context 钩子；
        2. 从 config 构建 ApiJob 配置并计算实体日期范围；
        3. 构建 ApiJobBundle 列表；
        4. 调用 on_before_fetch 钩子。
        
        Returns:
            List[ApiJob]: 预处理完成后的 ApiJob 列表，已注入日期范围等参数
        """
        from loguru import logger
        data_source_key = self.get_key()
        is_dry_run = self.context.get("is_dry_run", False)
        dry_run_status = " [DRY RUN]" if is_dry_run else ""
        logger.info(f"🔧 [{data_source_key}] 开始预处理阶段{dry_run_status}")

        # 1. 上下文准备
        self.on_prepare_context(self.context)

        # 2. 从 config 构建 ApiJob 配置
        config: DataSourceConfig = self.context.get("config")
        apis_conf = config.get_apis()

        # 4. Phase 1：一次性获取所有实体的 last_update 映射
        last_update_map = self._get_last_update_map()

        # 5. Phase 2：基于 last_update 映射计算各实体的 (start_date, end_date)
        entity_date_ranges = self._calculate_entity_date_ranges(last_update_map)
        
        # 将 last_update_map 和 entity_date_ranges 注入 context，供子类使用（特别是多字段分组场景）
        self.context["_last_update_map"] = last_update_map
        self.context["_entity_date_ranges"] = entity_date_ranges

        # 6. Phase 3：基于 entity_date_ranges 构建实际的 ApiJobBundle 列表
        if config.is_per_entity():
            jobs = self._build_jobs(apis_conf, entity_date_ranges)
        else:
            global_range = entity_date_ranges.get("_global")
            jobs = []
            if global_range:
                job = self._build_job(None, apis_conf, global_range)
                jobs = [job]

        jobs = self.on_before_fetch(self.context, jobs)
        
        data_source_key = self.get_key()
        is_dry_run = self.context.get("is_dry_run", False)
        dry_run_status = " [DRY RUN]" if is_dry_run else ""
        logger.info(f"🔧 [{data_source_key}] 预处理完成: {len(jobs)} 个 job bundles{dry_run_status}")

        return jobs

    def _get_entity_list(self) -> List[Any]:
        """
        获取 per-entity 的实体列表。仅当 result_group_by.list == "stock_list" 时从
        dependencies 解析；其他 list 名（如 "stock_index_list"）需由子类在 on_before_fetch
        等钩子中自行注入实体列表，本方法返回 []。
        
        优先级：
        1. context 中的 stock_list（handler 可能在 on_prepare_context 中修改了）
        2. dependencies 中的 stock_list
        """
        config = self.context.get("config")
        group_by_entity_list_name = (config.get_group_by_entity_list_name() if config else None) or ""

        if group_by_entity_list_name == "stock_list":
            # 优先使用 context 中的 stock_list（handler 可能在 on_prepare_context 中修改了）
            if "stock_list" in self.context:
                entity_list = self.context["stock_list"]
                return entity_list or []
            
            # 回退到 dependencies
            deps = self.context.get("dependencies") or {}
            entity_list = deps.get("stock_list")
            return (entity_list or []) if entity_list is not None else []
        if group_by_entity_list_name:
            raise ValueError(
                f"不支持的 result_group_by.list: {group_by_entity_list_name}。"
                "仅 'stock_list' 由基类从 dependencies 解析；其他实体列表请在 handler 的 on_before_fetch 中自行注入。"
            )
        return []

    def _get_last_update_map(self) -> Dict[str, Optional[str]]:
        """
        Phase 1：获取所有实体的“原始” last_update 映射（不考虑 renew_mode）。
        具体 DB 查询与标准化逻辑委托给 DataSourceHandlerHelper.compute_last_update_map。
        """
        return DataSourceHandlerHelper.compute_last_update_map(self.context)

    def _calculate_entity_date_ranges(
        self, last_update_map: Dict[str, Optional[str]]
    ) -> Dict[str, Tuple[str, str]]:
        """
        Phase 2：基于 last_update 映射 + renew_mode + renew_if_over_days，
        计算本次需要抓取的实体及其 (start_date, end_date)。

        实际计算逻辑委托给 DataSourceHandlerHelper.compute_entity_date_ranges，
        这里保留骨架，方便子类在必要时覆写。
        """
        return DataSourceHandlerHelper.compute_entity_date_ranges(self.context, last_update_map)

    def _build_jobs(
        self,
        apis_conf: Dict[str, Any],
        entity_date_ranges: Dict[str, Tuple[str, str]],
    ) -> List[ApiJobBundle]:
        from loguru import logger
        
        entity_list = self._get_entity_list()
        config: DataSourceConfig = self.context.get("config")
        entity_key_field = config.get_group_by_key()

        jobs: List[ApiJobBundle] = []

        for entity_info in entity_list:
            # 实体 ID 的来源遵循 config.result_group_by.key 这一单一约定
            if isinstance(entity_info, dict):
                entity_id = entity_info.get(entity_key_field)
            else:
                # 如果依赖里直接给的是字符串/数字（如 ts_code），则直接当作实体 ID
                entity_id = entity_info

            if not entity_id:
                continue

            entity_key = str(entity_id)
            date_range = entity_date_ranges.get(entity_key)
            if not date_range:
                # 该实体本次无需 renew（可能因为未过 renew_if_over_days 阈值）
                continue

            job_collection = self._build_job(entity_info, apis_conf, date_range)
            if job_collection is not None:
                jobs.append(job_collection)
        
        jobs = self.on_after_build_jobs(self.context, jobs, entity_date_ranges)
        
        return jobs

        
    def _build_job(
        self,
        entity_info: Any,
        apis_conf: Dict[str, Any],
        date_range: Tuple[str, str],
    ) -> ApiJobBundle:
        """
        Phase 3：基于 (start_date, end_date) 构建单个实体（或全局）的 ApiJobBundle。

        - 使用 apis_conf 构造 ApiJob 列表；
        - 将日期范围注入到每个 ApiJob.params 中；
        - 为 per-entity 场景生成带实体后缀的 bundle_id，便于日志与排查。
        """
        from copy import deepcopy

        start_date, end_date = date_range

        # 基于 config.apis 构造 ApiJob 列表（每个实体一份拷贝，避免共享 params）
        base_jobs = DataSourceHandlerHelper.build_api_jobs(apis_conf)
        apis: List[ApiJob] = []
        for job in base_jobs:
            cloned = ApiJob(
                api_name=job.api_name,
                provider_name=job.provider_name,
                method=job.method,
                params=deepcopy(job.params),
                api_params=deepcopy(job.api_params),
                depends_on=list(job.depends_on or []),
                rate_limit=job.rate_limit,
                job_id=job.job_id,
            )
            apis.append(cloned)

        # 注入统一的日期范围（per-entity 已由 entity_date_ranges 决定）
        apis = DataSourceHandlerHelper.add_date_range(apis, start_date, end_date)

        # per-entity 场景：构建 job payload（使用钩子方法，允许子类自定义如何提取实体 ID 并注入参数）
        entity_id = self.on_build_job_payload(entity_info, apis, self.context)

        # 构造 bundle_id：{data_source_key}_batch 或 {data_source_key}_batch_{entity_id}
        base_bundle_id = ApiJobBundle.to_id(self.get_key())

        # per-entity 场景：使用同一套实体 ID 约定（config.result_group_by.key）
        entity_suffix = entity_id if entity_id else None
        if entity_suffix is not None:
            bundle_id = f"{base_bundle_id}_{entity_suffix}"
        else:
            bundle_id = base_bundle_id

        job_collection = ApiJobBundle(
            bundle_id=bundle_id,
            apis=apis,
            tuple_order_map=None,
            start_date=start_date,
            end_date=end_date,
        )
        return job_collection
        

    def _inject_dependencies(self, dependencies_data):
        """注入依赖数据；无依赖时设为空字典，避免后续 .get 报错。"""
        self.context["dependencies"] = dependencies_data if dependencies_data is not None else {}
        # 从保留依赖 latest_trading_date 提取日期，供 context["latest_completed_trading_date"] 使用
        if dependencies_data and "latest_trading_date" in dependencies_data:
            val = dependencies_data["latest_trading_date"]
            if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict) and "date" in val[0]:
                self.context["latest_completed_trading_date"] = val[0]["date"]

    def _filter_by_renew_if_over_days(self, context: Dict[str, Any], apis: List[ApiJob]) -> List[ApiJob]:
        """
        根据 renew_if_over_days 配置过滤 ApiJobs。
        
        逻辑：
        1. 调用 check_renew_if_over_days 获取需要更新的 entity 列表
        2. 根据返回值过滤 ApiJobs：
           - None: 不过滤（全局数据且需要更新，或表为空）
           - []: 过滤掉所有 ApiJobs（全局数据且不需要更新）
           - List[str]: 只保留这些 entity 的 ApiJobs（per entity 模式）
        
        Args:
            context: 执行上下文
            apis: ApiJob 列表（已注入日期范围）
        
        Returns:
            List[ApiJob]: 过滤后的 ApiJob 列表
        """
        from loguru import logger
        
        config = self.context.get("config")
        if not config:
            return apis
        
        # 获取 renew_if_over_days 配置
        threshold_config = config.get_renew_if_over_days()
        if not threshold_config:
            return apis
        
        # 检查 renew_if_over_days
        stock_list = self.context.get("stock_list")
        need_update_entities = DataSourceHandlerHelper.check_renew_if_over_days(
            self.context, threshold_config, stock_list
        )
        
        # 根据返回值过滤 ApiJobs
        if need_update_entities is None:
            # 不过滤（全局数据且需要更新，或表为空）
            return apis
        
        if not need_update_entities:
            # 过滤掉所有 ApiJobs（全局数据且不需要更新）
            logger.info(f"renew_if_over_days 检查：没有需要更新的 entity，跳过所有 ApiJobs")
            return []
        
        # 只保留需要更新的 entity 的 ApiJobs（per entity 模式）
        need_update_set = set(need_update_entities)
        filtered_apis = []
        
        for job in apis:
            params = job.params or {}
            
            # 尝试从 params 中提取 entity_id（支持多种字段名）
            entity_id = (
                params.get("ts_code") or 
                params.get("code") or 
                params.get("stock_id") or
                params.get("id") or
                params.get("index_code")  # 用于指数
            )
            
            if entity_id and str(entity_id) in need_update_set:
                filtered_apis.append(job)
            elif not entity_id:
                # 如果无法提取 entity_id，保守策略：保留该 ApiJob
                logger.debug(f"ApiJob {job.job_id} 无法提取 entity_id，保留该 ApiJob")
                filtered_apis.append(job)
        
        logger.info(f"renew_if_over_days 检查：从 {len(apis)} 个 ApiJobs 过滤到 {len(filtered_apis)} 个")
        return filtered_apis



    # ================================
    # Executing stage
    # ================================
    def _executing(self, apis_job_bundles: List[ApiJob]) -> Dict[str, Any]:
        """
        执行阶段：按依赖关系执行 API 请求，并汇总结果。

        当前实现：单个批次（对应一只股票的所有API请求）。
        批次内的多个 API job 按依赖关系拓扑排序，同一阶段内的 job 并发执行。

        步骤：
        1. 构建 job 批次（_build_job_batch）；
        2. 调用 on_after_build_job_batch 钩子；
        3. 执行批次，并在执行过程中调用钩子：
           - 单个 api job 执行后：on_after_execute_single_api_job
           - 批次执行后：on_after_execute_job_batch
        4. 调用 on_after_fetch 钩子（全部执行完汇总后）；
        5. 错误处理：如果执行过程中出现异常，调用 on_error 钩子。

        Returns:
            Dict[str, Any]: 汇总后的抓取结果 {job_id: result}
        """
        try:

            fetched_data = self._multi_thread_execute(apis_job_bundles)

            fetched_data = self.on_before_normalize(self.context, fetched_data)

            return fetched_data
        except Exception as e:
            # 步骤 6：错误处理
            self.on_bundle_execution_error(e, self.context, apis_job_bundles)
            raise

    def _multi_thread_execute(self, jobs: List[Union["ApiJobBundle", ApiJob]]) -> Dict[str, Any]:
        """
        对 job bundles 进行多线程执行。

        - 若 jobs 为空，返回 {}。
        - 若仅有一个 bundle，在当前线程内用 ApiJobExecutor 执行后返回。
        - 若有多个 bundle，使用 MultiThreadWorker（多线程）并行执行每个 bundle，
          再合并各 bundle 的 {job_id: result}，并调用 on_after_single_api_job_bundle_complete 钩子。

        jobs 中每项可为 ApiJobBundle（含 .bundle_id、.apis）或单个 ApiJob（会当作仅含一个 job 的 bundle 处理）。
        """
        from loguru import logger
        import asyncio

        # 归一化：统一成 (bundle_id, apis, item) 列表，便于后续按 bundle_id 回调钩子
        bundles: List[Tuple[str, List[ApiJob], Any]] = []
        data_source_key = self.context.get("data_source_key", "data_source")

        for i, item in enumerate(jobs or []):
            if hasattr(item, "apis") and hasattr(item, "bundle_id"):
                # ApiJobBundle
                bid = getattr(item, "bundle_id", None) or f"{data_source_key}_bundle_{i}"
                apis = getattr(item, "apis", []) or []
                bundles.append((bid, apis, item))
            elif isinstance(item, ApiJob):
                # 单个 ApiJob 视为一个 bundle
                bid = getattr(item, "job_id", None) or f"{data_source_key}_job_{i}"
                bundles.append((bid, [item], item))
            else:
                logger.warning(f"未知 job 类型，已跳过: {type(item)}")
                continue

        if not bundles:
            return {}

        providers = self.context.get("providers") or {}
        executor = ApiJobExecutor(providers=providers)

        async def run_one_bundle(api_jobs: List[ApiJob]) -> Dict[str, Any]:
            if not api_jobs:
                return {}
            return await executor.execute(api_jobs)

        def _run_async_in_sync(coro):
            """在同步上下文中运行 async coro。若当前线程已有运行中的 loop 则在单独线程中起新 loop 执行，避免同线程内再跑一个 loop。"""
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
                                # 确保所有任务完成后再关闭 loop
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
                    # 确保所有任务完成后再关闭 loop
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
            logger.info(f"🔧 [single_bundle] 执行完成，准备调用钩子: bundle_id={bundle_id}, result_keys={list(result.keys())[:5] if isinstance(result, dict) else 'N/A'}...")
            # 根据 save_mode 决定是否调用钩子
            if save_mode != "unified" and hasattr(item, "apis") and hasattr(item, "bundle_id"):
                try:
                    logger.info(f"🔧 [single_bundle] 调用 on_after_single_api_job_bundle_complete: bundle_id={bundle_id}")
                    self.on_after_single_api_job_bundle_complete(self.context, item, result)
                    logger.info(f"✅ [single_bundle] on_after_single_api_job_bundle_complete 调用成功: bundle_id={bundle_id}")
                except Exception as e:
                    logger.error(f"❌ [single_bundle] on_after_single_api_job_bundle_complete 调用失败: bundle_id={bundle_id}, error={e}", exc_info=True)
            elif save_mode == "unified":
                logger.debug(f"🔧 [single_bundle] save_mode='unified'，跳过 on_after_single_api_job_bundle_complete（将在 _do_save 中统一保存）")
            else:
                logger.warning(f"⚠️ [single_bundle] item 没有 apis 或 bundle_id 属性，跳过钩子调用")
            logger.info(f"执行完成: 1/1 个 bundles")
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
                    completed = stats.get('completed_jobs', 0) + stats.get('failed_jobs', 0)
                    
                    # 每完成50个job输出一次进度
                    if completed >= last_reported_count + PROGRESS_INTERVAL:
                        current_percent = int((completed / total_bundles * 100)) if total_bundles > 0 else 0
                        logger.info(f"📊 进度: {completed}/{total_bundles} ({current_percent}%)")
                        # 更新到下一个50的倍数
                        last_reported_count = (completed // PROGRESS_INTERVAL) * PROGRESS_INTERVAL
                    
                    # 如果所有任务完成，输出最终进度并退出
                    if completed >= total_bundles:
                        if completed > last_reported_count:
                            current_percent = int((completed / total_bundles * 100)) if total_bundles > 0 else 0
                            logger.info(f"📊 进度: {completed}/{total_bundles} ({current_percent}%)")
                        break
                except Exception:
                    pass  # 忽略获取统计信息时的异常
                time.sleep(1)  # 每1秒检查一次
        
        progress_thread = threading.Thread(target=_progress_monitor, daemon=True)
        progress_thread.start()
        
        # 等待一小段时间，确保进度监控线程启动
        time.sleep(0.1)

        # 批量处理完成的结果：启动一个线程定期从 results_queue 中取出结果并批量调用钩子
        processed_results = set()  # 记录已处理的结果，避免重复处理
        pending_results = []  # 待处理的结果列表
        results_processing_stop = threading.Event()
        
        # 根据配置决定批量保存大小
        config = self.context.get("config")
        if not config or not hasattr(config, "get_save_mode"):
            raise ValueError("config 必须配置 save_mode")
        save_mode = config.get_save_mode()
        if save_mode == "immediate":
            BATCH_SAVE_SIZE = 1  # 立即保存：每个 bundle 完成后立即保存
        elif save_mode == "batch":
            BATCH_SAVE_SIZE = config.get_save_batch_size() if config and hasattr(config, "get_save_batch_size") else 50
        else:  # unified
            BATCH_SAVE_SIZE = float('inf')  # 统一保存：不在这里保存，在 _do_save 中统一保存
        
        def _has_actual_data(result_dict: Dict[str, Any]) -> bool:
            """
            检查结果字典是否真正包含数据。
            
            result_dict 的格式是 {job_id: result_data}，其中 result_data 可能是：
            - None: 执行失败
            - []: 空列表（API返回空数据）
            - [data]: 有数据的列表
            - DataFrame: pandas DataFrame
            
            只有当至少有一个 job_id 对应的 result_data 非空时，才返回 True。
            """
            if not isinstance(result_dict, dict) or not result_dict:
                return False
            
            import pandas as pd
            for job_id, result_data in result_dict.items():
                if result_data is None:
                    continue
                # 检查是否为 pandas DataFrame
                if isinstance(result_data, pd.DataFrame):
                    if not result_data.empty:
                        return True
                # 检查是否为列表或其他可迭代对象
                elif isinstance(result_data, (list, tuple)):
                    if len(result_data) > 0:
                        return True
                # 其他类型（如字典），检查是否非空
                elif result_data:
                    return True
            
            return False
        
        def _process_completed_results():
            """批量处理完成的结果：根据 save_mode 决定保存时机"""
            from queue import Empty
            while not results_processing_stop.is_set() or worker.is_running:
                try:
                    # 从 results_queue 中获取完成的结果
                    stats = worker.get_stats()
                    results_count = stats.get('results_count', 0)
                    
                    if results_count > 0:
                        # 获取所有可用的结果
                        available_results = worker.get_results()
                        for result in available_results:
                            if result.job_id in processed_results:
                                continue
                            
                            # 只处理成功完成且有数据的结果
                            if result.status == JobStatus.COMPLETED and _has_actual_data(result.result):
                                # 添加到待处理列表
                                pending_results.append(result)
                                
                                # 根据 save_mode 决定保存时机
                                # unified 模式：不在这里保存，在 _do_save 中统一保存
                                if save_mode == "unified":
                                    # unified 模式：不调用 on_after_single_api_job_bundle_complete
                                    processed_results.add(result.job_id)
                                    continue
                                
                                # immediate 或 batch 模式：当累积到 BATCH_SAVE_SIZE 个结果时，批量保存
                                if len(pending_results) >= BATCH_SAVE_SIZE:
                                    logger.info(f"🔧 [批量保存] 累积了 {len(pending_results)} 个有数据的结果，开始批量保存...")
                                    saved_count = 0
                                    for pending_result in pending_results:
                                        if pending_result.job_id in processed_results:
                                            continue
                                        
                                        processed_results.add(pending_result.job_id)
                                        
                                        # 调用钩子保存数据
                                        if pending_result.job_id in bundle_id_to_item:
                                            try:
                                                self.on_after_single_api_job_bundle_complete(
                                                    self.context, bundle_id_to_item[pending_result.job_id], pending_result.result
                                                )
                                                saved_count += 1
                                            except Exception as e:
                                                logger.error(f"❌ [批量保存] on_after_single_api_job_bundle_complete 调用失败: bundle_id={pending_result.job_id}, error={e}", exc_info=True)
                                    
                                    logger.info(f"✅ [批量保存] 完成 {saved_count}/{len(pending_results)} 个 bundles 的保存")
                                    pending_results.clear()  # 清空待处理列表
                            elif result.status == JobStatus.FAILED:
                                # 失败的结果也标记为已处理，避免重复处理
                                processed_results.add(result.job_id)
                                logger.debug(f"⚠️ [批量保存] Bundle {result.job_id} 失败，跳过")
                            elif result.status == JobStatus.COMPLETED:
                                # COMPLETED 但没有数据，标记为已处理但跳过
                                processed_results.add(result.job_id)
                                # 检查 result.result 的结构，提供更详细的日志
                                if isinstance(result.result, dict):
                                    job_count = len(result.result)
                                    import pandas as pd
                                    empty_jobs = []
                                    non_empty_jobs = []
                                    for job_id, data in result.result.items():
                                        is_empty = False
                                        if data is None:
                                            is_empty = True
                                        elif isinstance(data, pd.DataFrame):
                                            is_empty = data.empty
                                        elif isinstance(data, (list, tuple)):
                                            is_empty = len(data) == 0
                                        elif isinstance(data, dict):
                                            is_empty = len(data) == 0
                                        elif not data:  # 其他 falsy 值
                                            is_empty = True
                                        
                                        if is_empty:
                                            empty_jobs.append(job_id)
                                        else:
                                            non_empty_jobs.append(job_id)
                            else:
                                # 其他状态（PENDING、RUNNING等），标记为已处理但跳过
                                processed_results.add(result.job_id)
                    time.sleep(0.5)  # 每0.5秒检查一次
                except Exception as e:
                    logger.error(f"❌ [批量保存] 处理结果时出错: {e}", exc_info=True)
                    time.sleep(1)  # 出错后等待1秒再继续
        
        results_processing_thread = threading.Thread(target=_process_completed_results, daemon=True)
        results_processing_thread.start()
        
        try:
            worker.run_jobs()
        finally:
            progress_stop.set()  # 停止进度监控
            results_processing_stop.set()  # 停止结果处理
            # 等待进度线程结束（最多等待2秒）
            progress_thread.join(timeout=2)
            results_processing_thread.join(timeout=2)
        
        # 处理剩余的结果（可能有些结果在处理线程停止后才完成）
        results_list = worker.get_results()
        logger.info(f"🔧 [multi_thread] worker.run_jobs() 完成，获取到 {len(results_list)} 个剩余结果")

        # 处理剩余的结果（包括待处理列表中的和最后一批未达到批量大小的）
        # 先处理待处理列表中的剩余结果（仅 immediate 和 batch 模式）
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
                            self.on_after_single_api_job_bundle_complete(
                                self.context, bundle_id_to_item[pending_result.job_id], pending_result.result
                            )
                            saved_count += 1
                        except Exception as e:
                            logger.error(f"❌ [批量保存] on_after_single_api_job_bundle_complete 调用失败: bundle_id={pending_result.job_id}, error={e}", exc_info=True)
            logger.info(f"✅ [批量保存] 完成最后一批 {saved_count}/{len(pending_results)} 个 bundles 的保存")
            pending_results.clear()
        
        # 合并为 {job_id: result}，处理剩余的结果（已经在批量处理线程中处理过的会跳过）
        merged: Dict[str, Any] = {}
        completed_count = len(processed_results)  # 已处理的数量
        
        logger.info(f"🔧 [multi_thread] 开始处理 {len(results_list)} 个剩余结果（已批量处理 {completed_count} 个）")
        
        for r in results_list:
            # 跳过已经在批量处理线程中处理过的结果
            if r.job_id in processed_results:
                continue
                
            if r.status == JobStatus.COMPLETED and _has_actual_data(r.result):
                # 只处理有数据的结果
                merged.update(r.result)
                # unified 模式：不在这里调用钩子，在 _do_save 中统一保存
                if save_mode != "unified" and r.job_id in bundle_id_to_item:
                    try:
                        self.on_after_single_api_job_bundle_complete(
                            self.context, bundle_id_to_item[r.job_id], r.result
                        )
                        processed_results.add(r.job_id)
                        completed_count += 1
                    except Exception as e:
                        logger.error(f"❌ [剩余结果] on_after_single_api_job_bundle_complete 调用失败: bundle_id={r.job_id}, error={e}", exc_info=True)
                else:
                    # unified 模式：只标记为已处理，不调用钩子
                    processed_results.add(r.job_id)
                    completed_count += 1
            elif r.status == JobStatus.COMPLETED and not _has_actual_data(r.result):
                # 空结果，标记为已处理但跳过
                processed_results.add(r.job_id)
                # 检查 result.result 的结构，提供更详细的日志
                if isinstance(r.result, dict):
                    job_count = len(r.result)
                    empty_jobs = [job_id for job_id, data in r.result.items() 
                                if data is None or (isinstance(data, (list, tuple)) and len(data) == 0)]
                    logger.debug(
                        f"⚠️ [剩余结果] Bundle {r.job_id} 完成但无数据，跳过 "
                        f"(共 {job_count} 个 API jobs，全部为空: {empty_jobs[:3]}{'...' if len(empty_jobs) > 3 else ''})"
                    )
                else:
                    logger.debug(f"⚠️ [剩余结果] Bundle {r.job_id} 完成但结果格式异常，跳过 (result类型: {type(r.result)})")
            elif r.status == JobStatus.FAILED and r.error:
                logger.warning(f"Bundle {r.job_id} 失败: {r.error}")
                completed_count += 1
        
        logger.info(f"执行完成: {completed_count}/{total_bundles} 个 bundles（批量处理 {len(processed_results)} 个）")

        return merged

    # ================================
    # Postprocess stage
    # ================================
    def _postprocess(self, fetched_data: Any) -> Dict[str, Any]:
        logger.info(f"🔧 [_postprocess] 开始后处理阶段，fetched_data keys: {list(fetched_data.keys())[:5] if isinstance(fetched_data, dict) else 'N/A'}...")
        
        # 调用 normalize_data（子类可以覆盖此方法）
        normalized_data = self.normalize_data(self.context, fetched_data)
        logger.info(f"🔧 [_postprocess] normalize_data 完成，返回数据条数: {len(normalized_data.get('data', [])) if isinstance(normalized_data, dict) else 0}")

        normalized_data = self.on_after_normalize(self.context, normalized_data)

        normalized_data = self._validate_normalized_data(normalized_data)

        return normalized_data

    def _normalize_data(self, context: Dict[str, Any], fetched_data: Any):
        """
        标准化阶段：默认实现按“步骤大纲”调用 Helper，将原始数据转换为标准结构。

        步骤大纲：
        1. 从 context 中解析 apis 配置和 schema（输入准备）；
        2. 做一次字段覆盖校验：哪些 schema 字段在 field_mapping 中没有被任何 API 覆盖（仅日志提醒）；
        3. 遍历每个 API，取出对应结果并转换为 records（DataFrame → records 或 list[dict]）；
        4. 使用该 API 的 field_mapping 将原始字段映射到标准字段；
        5. 合并所有 API 的映射结果，得到统一的 records 列表；
        6. 使用 schema 约束字段集和类型（只保留 schema 定义的字段，并做类型转换/默认值填充）；
        7. 将最终记录包装为 {"data": [...]} 返回。

        复杂场景（多 API 复杂合并、自定义结构）应在子类中覆盖本方法。
        """
        from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper
        from core.utils.utils import Utils

        # 步骤 1：从 context 中解析 apis 配置和 schema（输入准备）
        config = context.get("config")
        # 使用 DataSourceConfig 的方法
        apis_conf = config.get_apis()
        schema = context.get("schema")

        if not fetched_data:
            # 原始数据为空或类型不对，直接返回空结果
            return {"data": []}

        # 步骤 2：做一次字段覆盖校验（提醒式，不中断执行；ignore_fields 不参与）
        ignore_fields = config.get_ignore_fields() if config else []
        DataSourceHandlerHelper.validate_field_coverage(apis_conf, schema, ignore_fields=ignore_fields)

        # 步骤 3 & 4：从所有 API 返回中提取并映射出标准字段记录
        # 检查是否配置了 merge_by_key（用于按 key 合并多个 API 的结果）
        merge_by_key = None
        if hasattr(config, "get_merge_by_key"):
            merge_by_key = config.get_merge_by_key()
        
        mapped_records: List[Dict[str, Any]] = DataSourceHandlerHelper.extract_mapped_records(
            apis_conf=apis_conf,
            fetched_data=fetched_data,
            merge_by_key=merge_by_key,
        )

        if not mapped_records:
            # 所有 API 都没有产生有效记录
            return {"data": []}

        # 步骤 4.4：自动日期标准化（如果配置了 date_format）
        # 根据 config.date_format 自动标准化 date 字段
        config = context.get("config")
        date_format = config.get_date_format() if config else None

        # 使用 DateUtils 的 period 规范化逻辑，将各种配置值统一为
        # "day" / "month" / "quarter"，再交给 normalize_date_field 处理。
        try:
            from core.utils.date.date_utils import DateUtils
            target_format = DateUtils.normalize_period_type(date_format or DateUtils.PERIOD_DAY)
        except Exception:
            # 极端情况下（例如循环依赖），回退为按天标准化，保持兼容
            target_format = "day"

        if target_format and target_format != "none":
            mapped_records = DataSourceHandlerHelper.normalize_date_field(
                mapped_records,
                field="date",
                target_format=target_format,
            )

        # 步骤 4.5：调用 on_after_mapping 钩子，允许子类在字段映射后、schema 应用前进行自定义处理
        # 例如：处理schema里定义过的但无法直接通过API得到的字段
        mapped_records = self.on_after_mapping(context, mapped_records)

        if not mapped_records:
            # 钩子过滤后没有有效记录
            return {"data": []}

        # 步骤 5 & 6：使用 schema 约束字段集和类型（只保留 schema 定义的字段，并做类型转换/默认值填充）
        normalized_records = DataSourceHandlerHelper.apply_schema(mapped_records, schema)

        # 步骤 7：将最终记录包装为 {"data": [...]} 返回
        return DataSourceHandlerHelper.build_normalized_payload(normalized_records)

    def normalize_data(self, context: Dict[str, Any], fetched_data: Any) -> Dict[str, Any]:
        """
        标准化数据钩子：子类可以覆盖此方法来自定义数据标准化逻辑。
        
        默认实现调用 _normalize_data 进行标准化的数据处理。
        
        Args:
            context: 执行上下文
            fetched_data: 抓取到的原始数据
            
        Returns:
            Dict[str, Any]: 标准化后的数据，格式为 {"data": [...]}
        """
        return self._normalize_data(context, fetched_data)

    def _validate_normalized_data(self, normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证标准化数据：验证标准化后的数据是否符合 schema。
        
        Args:
            normalized_data: 标准化后的数据
            
        Returns:
            Dict[str, Any]: 验证后的数据（如果验证失败会抛出异常）
        """
        schema = self.context.get("schema")
        config = self.context.get("config")
        data_source_key = self.context.get("data_source_key", "unknown")
        ignore_fields = config.get_ignore_fields() if config else []
        DataSourceHandlerHelper.validate_normalized_data(
            normalized_data, schema, data_source_key, ignore_fields=ignore_fields
        )
        return normalized_data

    def _is_dry_run(self) -> bool:
        """
        是否处于试跑模式（不执行任何 DB 写入）。
        从 context["is_dry_run"] 读取，由框架在 _preprocess 中根据 config 顶层 is_dry_run 注入。
        """
        return bool(self.context.get("is_dry_run", False))

    def _do_save(self, normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        在非 is_dry_run 时执行写入：先调用用户钩子 on_before_save，再系统写入绑定表。
        on_before_save 若返回非 None，则用其作为即将写入的数据；否则使用传入的 normalized_data。
        is_dry_run 为 True 时不执行任何写入，直接返回 normalized_data。
        
        如果 save_mode == "per_bundle" 且 normalized_data 为空，跳过保存
        （数据已在 on_after_single_api_job_bundle_complete 中保存）。
        """
        config = self.context.get("config")
        if not config or not hasattr(config, "get_save_mode"):
            raise ValueError("config 必须配置 save_mode")
        save_mode = config.get_save_mode()
        
        # 检查是否按批次保存且数据已保存
        if save_mode in ["immediate", "batch"]:
            data_list = normalized_data.get("data", []) if isinstance(normalized_data, dict) else []
            if not data_list:
                logger.info(f"🔧 [_do_save] save_mode='{save_mode}' 且数据为空，跳过统一保存（数据已在 on_after_single_api_job_bundle_complete 中保存）")
                return normalized_data
        
        logger.info(f"🔧 [_do_save] 开始保存阶段，normalized_data 数据条数: {len(normalized_data.get('data', [])) if isinstance(normalized_data, dict) else 0}")
        if self._is_dry_run():
            logger.info(f"🔧 [_do_save] Dry run 模式，跳过保存")
            return normalized_data
        resolved = self.on_before_save(self.context, normalized_data)
        data_to_save = resolved if resolved is not None else normalized_data
        logger.info(f"🔧 [_do_save] 准备调用 _system_save，数据条数: {len(data_to_save.get('data', [])) if isinstance(data_to_save, dict) else 0}")
        self._system_save(data_to_save)
        logger.info(f"🔧 [_do_save] _system_save 完成")
        return data_to_save

    def _system_save(self, normalized_data: Dict[str, Any]) -> None:
        """
        将标准化数据写入绑定表（使用表 schema 的 primaryKey 做 upsert）。
        仅框架内部调用；用户自定义写入请在 on_before_save 中实现。
        """
        from loguru import logger
        config = self.context.get("config")
        data_manager = self.context.get("data_manager")
        schema = self.context.get("schema")
        if not config or not data_manager or not schema:
            return
        table_name = config.get_table_name()
        if not table_name:
            return
        model = data_manager.get_table(table_name)
        if not model or not hasattr(model, "upsert_many"):
            logger.warning(f"表 {table_name} 未注册或无可用的 upsert_many，跳过系统写入")
            return
        records = (normalized_data or {}).get("data")
        if not records or not isinstance(records, list):
            logger.debug(f"系统写入 {table_name}: normalized_data 中没有数据或格式不正确，跳过写入")
            return
        pk = schema.get("primaryKey")
        if isinstance(pk, str):
            unique_keys = [pk]
        elif isinstance(pk, list):
            unique_keys = list(pk)
        else:
            unique_keys = None
        try:
            logger.info(f"系统写入 {table_name}: 准备写入 {len(records)} 条记录，unique_keys={unique_keys}")
            if unique_keys:
                count = model.upsert_many(records, unique_keys=unique_keys)
            else:
                count = model.insert_many(records)
            logger.info(f"系统写入 {table_name}: {count} 条")
        except Exception as e:
            logger.error(f"系统写入 {table_name} 失败: {e}")
            raise

    # ================================
    # Hooks
    # ================================

    def on_prepare_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        预处理阶段的上下文准备钩子：在注入全局依赖之后、构建 ApiJobs 之前调用。

        设计意图：
        - 作为“集中注入/派生上下文数据”的入口，避免在各个钩子中零散修改 context；
        - 典型用途包括：
          - 基于全局依赖派生字段（如 last_update、index_map 等）；
          - 预先查询并缓存后续步骤会频繁使用的数据；
          - 注入与本次执行强相关的业务状态。

        默认行为：
        - 如果 latest_completed_trading_date 缺失，自动从 data_manager 获取

        Args:
            context: 当前执行上下文（已注入全局依赖）

        Returns:
            Dict[str, Any]: 处理后的上下文字典
        """
        # 如果 latest_completed_trading_date 缺失，自动获取
        if "latest_completed_trading_date" not in context or not context.get("latest_completed_trading_date"):
            data_manager = context.get("data_manager")
            if data_manager:
                try:
                    latest_completed_trading_date = data_manager.service.calendar.get_latest_completed_trading_date()
                    context["latest_completed_trading_date"] = latest_completed_trading_date
                except Exception:
                    # 如果获取失败，保持原样（可能后续步骤会处理）
                    pass
        
        return context

    def on_calculate_date_range(
        self, 
        context: Dict[str, Any], 
        apis: List[ApiJob]
    ) -> Optional[Union[Tuple[str, str], Dict[str, Tuple[str, str]]]]:
        """
        计算日期范围的钩子：允许子类实现自定义的日期范围计算逻辑。

        如果返回 None，将使用默认的 RenewManager 逻辑（根据 renew_mode 自动计算）。
        如果返回日期范围（单个或 per stock），将直接使用该结果，跳过默认逻辑。

        适用场景：
        - 需要复杂的日期范围计算逻辑（例如：基于多个表的联合查询）
        - 需要特殊的 renew 策略（例如：基于业务规则的动态日期范围）
        - 需要自定义的 per stock 日期范围计算

        Args:
            context: 执行上下文（包含 config, data_manager, stock_list 等）
            apis: ApiJob 列表（尚未注入日期范围）

        Returns:
            - None: 使用默认的 RenewManager 逻辑
            - Tuple[str, str]: 统一的日期范围 (start_date, end_date)
            - Dict[str, Tuple[str, str]]: per stock 的日期范围 {stock_id: (start_date, end_date)}
        """
        return None

    def _extract_entity_id(
        self, 
        entity_info: Any, 
        entity_key_field: str, 
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        提取实体 ID 的内部辅助方法：供 on_build_job_payload 的默认实现使用。
        
        注意：此方法为内部方法（以下划线开头），不建议子类直接使用。
        子类应该覆盖 on_build_job_payload 来自定义提取和注入逻辑。
        
        Args:
            entity_info: 实体信息（来自 dependencies，如 stock_list 中的一项）
            entity_key_field: 实体键字段名（来自 config.result_group_by.key，通常是 "id"）
            context: 执行上下文
            
        Returns:
            str: 提取的实体 ID，如果无法提取则返回 None
        """
        if not isinstance(entity_info, dict):
            return str(entity_info) if entity_info is not None else None
        
        return entity_info.get(entity_key_field)

    def on_build_job_payload(
        self,
        entity_info: Any,
        apis: List[ApiJob],
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        构建 job payload 的钩子：在构建 ApiJobBundle 时，为每个 API job 组装请求参数（payload）。
        
        此钩子在 _build_job 方法中调用，用于：
        1. 从 entity_info 中提取实体 ID
        2. 将实体 ID 注入到每个 API job 的 params 中
        
        默认实现：仅提取实体 ID 并返回，不进行参数注入。
        子类必须覆盖此方法来实现具体的参数注入逻辑。
        
        子类可以覆盖此方法来：
        - 使用固定的字段名（如 "id"）提取实体 ID
        - 自定义实体 ID 的格式转换
        - 手动注入参数到 job.params（如 ts_code、stock_id 等）
        
        Args:
            entity_info: 实体信息（来自 dependencies，如 stock_list 中的一项）
            apis: ApiJob 列表（已注入日期范围，但尚未注入实体参数）
            context: 执行上下文
            
        Returns:
            Optional[str]: 提取的实体 ID（用于构建 bundle_id），如果不需要注入或无法提取则返回 None
        """
        if not entity_info:
            return None
        
        config: DataSourceConfig = context.get("config")
        if not config:
            return None
        
        # 获取实体标识字段：多字段分组时使用第一个字段，单字段分组时使用 key
        entity_key_field = None
        group_fields = config.get_group_fields() if hasattr(config, "get_group_fields") else []
        if group_fields and len(group_fields) > 0:
            entity_key_field = group_fields[0]  # 多字段分组时，第一个字段是主键（如 id）
        else:
            entity_key_field = config.get_group_by_key()  # 单字段分组
        
        if not entity_key_field:
            return None
        
        # 提取实体 ID：使用内部辅助方法
        entity_id = self._extract_entity_id(entity_info, entity_key_field, context)
        
        # 默认实现：仅返回实体 ID，不进行参数注入
        # 子类需要覆盖此方法来手动注入参数
        return str(entity_id) if entity_id else None

    def on_after_build_jobs(
        self, 
        context: Dict[str, Any], 
        jobs: List[ApiJobBundle],
        entity_date_ranges: Dict[str, Tuple[str, str]]
    ) -> List[ApiJobBundle]:
        """
        Jobs 构建完成后的钩子：允许子类在 jobs 构建完成后进行修改（如 merge、过滤等）。

        在 _build_jobs 完成后调用，子类可以：
        - 合并多个 jobs（如将同一实体的多个周期合并为一个 bundle）
        - 过滤不需要的 jobs
        - 调整 jobs 的顺序或配置

        Args:
            context: 上下文信息
            jobs: 已构建的 ApiJobBundle 列表
            entity_date_ranges: 实体日期范围映射（key 可能是复合 key，如 "stock_id::term"）

        Returns:
            List[ApiJobBundle]: 处理后的 ApiJobBundle 列表
        """
        return jobs

    def on_before_fetch(self, context: Dict[str, Any], apis: List[ApiJob]) -> List[ApiJob]:
        """
        抓取前阶段钩子：允许子类基于 context 调整 ApiJobs。

        在日期范围已注入到 ApiJobs 之后调用，子类可以：
        - 基于日期范围或其他条件调整 ApiJob 参数
        - 添加或移除 ApiJob
        - 修改 ApiJob 的依赖关系

        Args:
            context: 上下文信息
            apis: ApiJob 列表（已注入日期范围）

        Returns:
            List[ApiJob]: 处理后的 ApiJob 列表
        """
        return apis

    def on_after_single_api_job_complete(self, context: Dict[str, Any], job: ApiJobBundle, fetched_data: Dict[str, Any]) -> ApiJobBundle:
        """
        批次构建后的钩子。

        在 job batch 构建完成后调用，子类可以：
        - 检查批次配置
        - 调整批次内的 ApiJobs
        - 记录批次信息

        Args:
            context: 上下文信息
            job_batch: 构建好的批次

        Returns:
            ApiJobBatch: 处理后的批次（默认返回原批次）
        """
        return fetched_data

    def on_single_job_failed():
        pass

    def on_after_single_api_job_bundle_complete(self, context: Dict[str, Any], job_bundle: ApiJobBundle, fetched_data: Dict[str, Any]):
        """
        执行单个 api job bundle 后的钩子。
        
        保存时机由 config.save_mode 控制：
        - "unified"（默认）：不在此钩子中保存，数据会在 _do_save 中统一保存
        - "immediate"：每个 bundle 完成后立即调用此钩子保存数据
        - "batch"：累计 save_batch_size 个 bundle 后批量调用此钩子保存数据
        
        如果 save_mode != "unified"，子类应该在此钩子中保存数据，
        并在 normalize_data 中返回空数据，避免重复保存。
        """
        return fetched_data

    def on_job_bundle_failed():
        pass

    def on_one_thread_execution_complete(self, context: Dict[str, Any], fetched_data: Dict[str, Any]):
        """
        单线程执行完成后的钩子。
        """
        return fetched_data
    
    def on_thread_execution_error(self, error: Exception, context: Dict[str, Any], apis: List[ApiJob]) -> None:
        """
        执行错误时的钩子。

        当执行阶段（_executing）出现异常时调用此钩子。
        子类可以覆盖此方法来实现自定义错误处理逻辑，例如：
        - 记录错误日志
        - 清理资源
        - 重试机制
        - 错误通知

        注意：此钩子不会阻止异常传播，异常仍会向上抛出。

        Args:
            error: 发生的异常
            context: 上下文信息
            apis: 执行时的 ApiJob 列表
        """
        from loguru import logger
        data_source_key = context.get("data_source_key", "unknown")
        logger.error(f"❌ 数据源 {data_source_key} 执行失败: {error}")


    def on_after_fetch(self, context: Dict[str, Any], fetched_data: Dict[str, Any], apis: List[ApiJob]):
        """
        抓取完成后的预处理钩子（标准化之前）。

        默认行为：在编排层先判断是否存在 `group_by` 配置：
        - 如果至少有一个 API 配置了 `group_by`，则调用
          `DataSourceHandlerHelper.build_grouped_fetched_data`，按实体分组；
        - 如果所有 API 都未配置 `group_by`，则调用
          `DataSourceHandlerHelper.build_unified_fetched_data`，按 api_name 聚合到 `_unified`。

        这样可以让「有实体分组」与「纯全局数据」两条路径在编排层语义更清晰。
        """
        if DataSourceHandlerHelper.has_group_by_config(context, apis):
            return DataSourceHandlerHelper.build_grouped_fetched_data(context, fetched_data, apis)
        return DataSourceHandlerHelper.build_unified_fetched_data(context, fetched_data, apis)

    def on_before_normalize(self, context: Dict[str, Any], fetched_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化前钩子：默认实现直接返回 fetched_data。

        子类可覆盖此方法，在 normalize 之前对抓取结果做进一步预处理，
        例如字段合并、结构调整、补充上下文信息等。
        """
        return fetched_data

    def on_after_mapping(self, context: Dict[str, Any], mapped_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        字段映射后的钩子：允许子类在字段映射后、schema 应用前进行自定义处理。

        常见用途：
        - 从 context 添加字段（如 last_update、当前时间等）
        - 过滤记录（如只保留有效的记录）
        - 数据转换（如字段重命名、格式转换等）
        - 添加计算字段

        Args:
            context: 执行上下文
            mapped_records: 已应用 field_mapping 的记录列表

        Returns:
            List[Dict[str, Any]]: 处理后的记录列表（如果返回空列表，后续步骤会返回空数据）
        """
        return mapped_records

    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]):
        """
        标准化后的钩子：默认行为是自动清洗 NaN 值，然后返回数据。

        子类可以覆盖此方法来自定义清洗逻辑，或跳过清洗（直接返回 normalized_data）。

        默认清洗策略：
        - 如果 config.date_format 为 "day" 或 "month"，默认值使用 0.0（数值数据）
        - 否则使用 None（可能包含非数值字段）

        默认清洗策略：
        - 如果 config.date_format 为 "day" 或 "month"，默认值使用 0.0（数值数据）
        - 否则使用 None（可能包含非数值字段）
        """
        config = context.get("config")
        date_format = config.get_date_format()
        
        # 根据 date_format 决定默认值
        if date_format in ("day", "month"):
            default = 0.0
        else:
            default = None
        
        # 自动清洗 NaN
        return self.clean_nan_in_normalized_data(normalized_data, default=default)

    def on_before_run(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        流程开始前钩子：在 _preprocess 之前调用。
        若返回非 None，框架将该值作为 execute() 的结果直接返回，跳过 fetch / normalize / save 等后续所有步骤。
        若返回 None，继续正常流程。可用于实现「有缓存则直接返回 DB 数据」等短路逻辑。
        """
        return None

    def on_before_save(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        用户 save 钩子：在系统写入绑定表之前调用。
        若返回非 None，框架用返回值作为即将写入绑定表的数据（并作为本次 execute 的最终结果）；
        返回 None 则使用传入的 normalized_data。可用于在写入前做字段解析（如 name→id、is_alive 等）。
        context["is_dry_run"] 为 True 时不会调用本钩子，也不会执行系统写入。
        """
        return None

    def on_bundle_execution_error(self, error: Exception, context: Dict[str, Any], apis: List[ApiJob]) -> None:
        """
        执行错误时的钩子。

        当执行阶段（_executing）出现异常时调用此钩子。
        子类可以覆盖此方法来实现自定义错误处理逻辑，例如：
        - 记录错误日志
        - 清理资源
        - 重试机制
        - 错误通知

        Args:
            error: 发生的异常
            context: 上下文信息
            apis: 执行时的 ApiJob 列表
        """

    # ================================
    # 通用辅助方法（暴露给子类使用）
    # ================================

    @staticmethod
    def clean_nan_in_records(records: List[Dict[str, Any]], default: Any = None) -> List[Dict[str, Any]]:
        """
        清理一批记录中的 NaN/None 等异常数值，返回清洗后的记录列表。

        内部委托 DataSourceHandlerHelper 和 DBHelper 实现，子类无需关心具体细节。
        """
        return DataSourceHandlerHelper.clean_nan_in_records(records, default=default)

    @staticmethod   
    def clean_nan_in_normalized_data(normalized_data: Dict[str, Any], default: Any = None) -> Dict[str, Any]:
        """
        针对标准化结果的便捷 NaN 清洗：
        - 如果 normalized_data 是 {"data": [...]}，则对 data 列表做清洗；
        - 否则尝试直接将 normalized_data 视为单条记录列表的一部分。
        """
        if not normalized_data:
            return normalized_data

        if isinstance(normalized_data, dict) and "data" in normalized_data:
            data_list = normalized_data.get("data") or []
            if isinstance(data_list, list):
                normalized_data["data"] = BaseHandler.clean_nan_in_records(data_list, default=default)
            return normalized_data

        # fallback：如果不是 {"data": [...]} 结构，则保持原样返回
        return normalized_data

    @staticmethod
    def filter_records_by_required_fields(
        records: List[Dict[str, Any]], required_fields: List[str]
    ) -> List[Dict[str, Any]]:
        """
        过滤记录：只保留包含所有必需字段的记录。

        Args:
            records: 记录列表
            required_fields: 必需字段列表

        Returns:
            List[Dict[str, Any]]: 过滤后的记录列表
        """
        if not records or not required_fields:
            return records
        return [r for r in records if all(r.get(f) for f in required_fields)]

    @staticmethod       
    def ensure_float_field(
        records: List[Dict[str, Any]], field: str, default: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        确保某个字段是 float 类型，转换失败时使用默认值。

        Args:
            records: 记录列表
            field: 字段名
            default: 转换失败时的默认值

        Returns:
            List[Dict[str, Any]]: 处理后的记录列表（原地修改）
        """
        if not records or not field:
            return records

        from loguru import logger

        for r in records:
            if not isinstance(r, dict):
                continue
            value = r.get(field)
            if value is None:
                r[field] = default
            else:
                try:
                    r[field] = float(value)
                except (ValueError, TypeError):
                    logger.warning(f"字段 {field} 无法转换为 float: {value}，使用默认值 {default}")
                    r[field] = default

        return records
