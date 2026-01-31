from typing import Any, Dict, List, Tuple, Optional, Union

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
        1. _preprocess：预处理阶段（构建 ApiJobs、计算日期范围、调用 on_before_fetch 钩子）；
        2. _executing：执行阶段（构建批次、执行 API 请求、调用 on_after_fetch 钩子）；
        3. _postprocess：后处理阶段（标准化数据、调用 on_after_normalize 钩子、数据验证）；
        4. _do_save：非 is_dry_run 时先调用 on_before_save（用户 save），再系统写入绑定表；
        5. 返回标准化后的数据。
        """
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
        
        步骤：
        1. 注入全局依赖到 context（_inject_required_global_dependencies）；
        2. 调用 on_prepare_context 钩子，允许子类基于依赖派生/注入额外的上下文数据；
        3. 从 config 构建 ApiJob 列表（_config_to_api_jobs）；
        4. 计算日期范围并注入到 ApiJobs 中（_add_date_range_to_api_jobs）；
        5. 调用 on_before_fetch 钩子，允许子类调整 ApiJobs；
        6. 检查 renew_if_over_days，过滤不需要更新的 entity（_filter_by_renew_if_over_days）。
        
        Returns:
            List[ApiJob]: 预处理完成后的 ApiJob 列表，已注入日期范围等参数
        """

        # 1. 注入全局依赖
        self._inject_dependencies(dependencies_data)

        # 2. 从 config 注入 is_dry_run 到 context（方便用户与框架读取）
        config = self.context.get("config")
        self.context["is_dry_run"] = bool(config.get("is_dry_run", False) if config else False)

        self.on_prepare_context(self.context)

        # 3. 从 config 构建 ApiJob 配置
        config: DataSourceConfig = self.context.get("config")
        apis_conf = config.get_apis()

        # 4. Phase 1：一次性获取所有实体的 last_update 映射
        last_update_map = self._get_last_update_map()

        # 5. Phase 2：基于 last_update 映射计算各实体的 (start_date, end_date)
        entity_date_ranges = self._calculate_entity_date_ranges(last_update_map)

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

        return jobs

    def _get_entity_list(self) -> List[Any]:
        """
        获取 per-entity 的实体列表。仅当 result_group_by.list == "stock_list" 时从
        dependencies 解析；其他 list 名（如 "stock_index_list"）需由子类在 on_before_fetch
        等钩子中自行注入实体列表，本方法返回 []。
        """
        config = self.context.get("config")
        group_by_entity_list_name = (config.get_group_by_entity_list_name() if config else None) or ""

        if group_by_entity_list_name == "stock_list":
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

        entity_list = self._get_entity_list()
        config: DataSourceConfig = self.context.get("config")
        entity_key_field = config.get_group_by_key()

        jobs: List[ApiJobBundle] = []

        for entity_info in entity_list:
            # 实体 ID 的来源遵循 config.result_group_by.by_key 这一单一约定
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

        # 构造 bundle_id：{data_source_key}_batch 或 {data_source_key}_batch_{entity_id}
        base_bundle_id = ApiJobBundle.to_id(self.get_key())

        # per-entity 场景：使用同一套实体 ID 约定（config.result_group_by.by_key）
        entity_suffix = None
        config: DataSourceConfig = self.context.get("config")
        entity_key_field = config.get_group_by_key()
        if entity_info:
            if isinstance(entity_info, dict):
                entity_suffix = entity_info.get(entity_key_field)
            else:
                entity_suffix = entity_info

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
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        def _in_thread():
                            new_loop = asyncio.new_event_loop()
                            try:
                                asyncio.set_event_loop(new_loop)
                                return new_loop.run_until_complete(coro)
                            finally:
                                new_loop.close()
                        future = pool.submit(_in_thread)
                        return future.result()
                return loop.run_until_complete(coro)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()

        # 仅一个 bundle：直接执行
        if len(bundles) == 1:
            bundle_id, apis, item = bundles[0]
            result = _run_async_in_sync(run_one_bundle(apis))
            if hasattr(item, "apis") and hasattr(item, "bundle_id"):
                self.on_after_single_api_job_bundle_complete(self.context, item, result)
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

        worker.run_jobs()
        results_list = worker.get_results()

        # 合并为 {job_id: result}，并对每个 bundle 触发 on_after_single_api_job_bundle_complete
        merged: Dict[str, Any] = {}
        for r in results_list:
            if r.status == JobStatus.COMPLETED and isinstance(r.result, dict):
                merged.update(r.result)
                if r.job_id in bundle_id_to_item:
                    self.on_after_single_api_job_bundle_complete(
                        self.context, bundle_id_to_item[r.job_id], r.result
                    )
            elif r.status == JobStatus.FAILED and r.error:
                logger.warning(f"Bundle {r.job_id} 失败: {r.error}")

        return merged

    # ================================
    # Postprocess stage
    # ================================
    def _postprocess(self, fetched_data: Dict[str, Any]) -> Dict[str, Any]:

        normalized_data = self._normalize_data(self.context, fetched_data)

        normalized_data = self.on_after_normalize(self.context, normalized_data)

        normalized_data = self._validate_normalized_data(normalized_data)

        return normalized_data

    def _normalize_data(self, context: Dict[str, Any], fetched_data: Dict[str, Any]):
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

        # 步骤 1：从 context 中解析 apis 配置和 schema（输入准备）
        config = context.get("config")
        # 使用 DataSourceConfig 的方法
        apis_conf = config.get_apis()
        schema = context.get("schema")

        if not fetched_data or not isinstance(fetched_data, dict):
            # 原始数据为空或类型不对，直接返回空结果
            return {"data": []}

        # 步骤 2：做一次字段覆盖校验（提醒式，不中断执行）
        DataSourceHandlerHelper.validate_field_coverage(apis_conf, schema)

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
        date_format = config.get_date_format()
        if date_format != "none":
            # 将 date_format 映射到 target_format
            # "day" -> "day", "month" -> "month", "quarter" -> "quarter"
            target_format = date_format if date_format in ("day", "month", "quarter") else "day"
            mapped_records = DataSourceHandlerHelper.normalize_date_field(
                mapped_records,
                field="date",
                target_format=target_format
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


    def _validate_normalized_data(self, normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证标准化数据：验证标准化后的数据是否符合 schema。
        
        Args:
            normalized_data: 标准化后的数据
            
        Returns:
            Dict[str, Any]: 验证后的数据（如果验证失败会抛出异常）
        """
        schema = self.context.get("schema")
        data_source_key = self.context.get("data_source_key", "unknown")
        DataSourceHandlerHelper.validate_normalized_data(normalized_data, schema, data_source_key)
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
        is_dry_run 为 True 时不执行任何写入，直接返回 normalized_data。
        """
        if self._is_dry_run():
            return normalized_data
        self.on_before_save(self.context, normalized_data)
        self._system_save(normalized_data)
        return normalized_data

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
        if not model or not hasattr(model, "batch_insert"):
            logger.warning(f"表 {table_name} 未注册或无可用的 batch_insert，跳过系统写入")
            return
        records = (normalized_data or {}).get("data")
        if not records or not isinstance(records, list):
            return
        pk = schema.get("primaryKey")
        if isinstance(pk, str):
            unique_keys = [pk]
        elif isinstance(pk, list):
            unique_keys = list(pk)
        else:
            unique_keys = None
        try:
            count = model.batch_insert(records, unique_keys=unique_keys)
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

        默认行为：直接返回传入的 context，不做任何修改。

        Args:
            context: 当前执行上下文（已注入全局依赖）

        Returns:
            Dict[str, Any]: 处理后的上下文字典
        """
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

    def on_before_save(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> None:
        """
        用户 save 钩子：在系统写入绑定表之前调用，供子类做自定义写入（如写其他表、打日志等）。
        执行顺序：用户 on_before_save → 系统写入 config 绑定的表。
        context["is_dry_run"] 为 True 时不会调用本钩子，也不会执行系统写入。
        """
        pass

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
