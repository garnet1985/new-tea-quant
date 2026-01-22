from typing import Any, Dict, List, Tuple, Optional, Union

from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper
from core.modules.data_source.service.api_job_executor import ApiJobExecutor
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.data_class.api_job_batch import ApiJobBatch
from core.modules.data_source.data_class.config import DataSourceConfig
from core.modules.data_source.data_class.schema import DataSourceSchema
from core.modules.data_source.renew_manager import RenewManager
from core.global_enums.enums import UpdateMode
from core.modules.data_manager.data_manager import DataManager



class BaseHandler:
    """
    Base Handler class
    """
    def __init__(self, data_source_name: str, schema: DataSourceSchema, config: DataSourceConfig, providers: Dict[str, BaseProvider]):
        self.context = {
            "data_source_name": data_source_name,
            "schema": schema,
            "config": config,
            "providers": providers,
            "data_manager": DataManager.get_instance(),
        }
        # self.apis: List[ApiJob] = []
        # self.fetched_data: Dict[str, Any] = {}
        # self.normalized_data: Dict[str, Any] = {}

    def execute(self, global_dependencies: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handler 的同步执行入口（默认实现）。

        流程大纲：
        1. _preprocess：预处理阶段（构建 ApiJobs、计算日期范围、调用 on_before_fetch 钩子）；
        2. _executing：执行阶段（构建批次、执行 API 请求、调用 on_after_fetch 钩子）；
        3. _postprocess：后处理阶段（标准化数据、调用 on_after_normalize 钩子、数据验证）；
        4. 返回标准化后的数据。
        """
        apis_jobs = self._preprocess(global_dependencies)

        fetched_data = self._executing(apis_jobs)

        normalized_data = self._postprocess(fetched_data)

        # apis = self.on_before_fetch(self.context, self.apis)
        # self.fetched_data = self.on_fetch(self.context, apis)
        # self.fetched_data = self.on_after_fetch(self.context, self.fetched_data, apis)
        # self.normalized_data = self.on_normalize(self.context, self.fetched_data)
        # self.normalized_data = self.on_after_normalize(self.context, self.normalized_data)

        # # 执行尾部数据验证：验证标准化后的数据是否符合 schema
        # schema = self.context.get("schema")
        # data_source_name = self.context.get("data_source_name", "unknown")
        # DataSourceHandlerHelper.validate_normalized_data(self.normalized_data, schema, data_source_name)

        return normalized_data

    def _preprocess(self, global_dependencies: Dict[str, Any]) -> List[ApiJob]:
        """
        预处理阶段：在执行 API 请求前的所有准备工作。

        步骤：
        1. 从 config 构建 ApiJob 列表（_config_to_api_jobs）；
        2. 计算日期范围并注入到 ApiJobs 中（_calculate_date_range）；
        3. 调用 on_before_fetch 钩子，允许子类调整 ApiJobs。

        Returns:
            List[ApiJob]: 预处理完成后的 ApiJob 列表，已注入日期范围等参数
        """
        self.context = self._inject_required_global_dependencies(global_dependencies)
        apis_jobs = self._config_to_api_jobs()
        apis_jobs = self._add_date_range_to_api_jobs(self.context, apis_jobs)
        apis_jobs = self.on_before_fetch(self.context, apis_jobs)
        return apis_jobs
        

    def _executing(self, apis_jobs: List[ApiJob]) -> Dict[str, Any]:
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
            # 步骤 1：构建 job 批次（当前实现：单个批次，包含所有 apis）
            job_batch = self._build_api_job_batch_per_stock(self.context, apis_jobs)

            # 步骤 2：调用批次构建后的钩子
            job_batch = self.on_after_build_job_batch_for_single_stock(self.context, job_batch)

            # 步骤 3：执行批次并调用钩子
            batch_results = self._execute_job_batch_for_single_stock(self.context, job_batch, apis_jobs)
            # 调用批次执行后的钩子
            self.on_after_execute_job_batch_for_single_stock(self.context, job_batch, batch_results)

            # 步骤 4 & 5：汇总结果并调用 on_after_fetch 钩子
            fetched_data = self.on_after_fetch(self.context, batch_results, apis_jobs)

            return fetched_data
        except Exception as e:
            # 步骤 6：错误处理
            self.on_error(e, self.context, apis_jobs)
            raise

    def _postprocess(self, fetched_data: Dict[str, Any]) -> Dict[str, Any]:

        normalized_data = self._normalize_data(self.context, fetched_data)

        normalized_data = self.on_after_normalize(self.context, normalized_data)

        normalized_data = self._validate_normalized_data(normalized_data)

        return normalized_data

    def _config_to_api_jobs(self) -> List[ApiJob]:
        """
        第一步：将 config 中声明的 apis 转换为 ApiJob 列表。

        职责：
        - 这里只负责描述“要调用哪些 API”，不关心如何执行和限流；
        - 具体转换规则由 DataSourceHandlerHelper.build_api_jobs 负责。
        """
        config = self.context.get("config")
        # 支持 DataSourceConfig 实例或 dict（兼容性）
        if hasattr(config, "get_apis"):
            api_conf = config.get_apis()
        else:
            api_conf = config.get("apis") if config else {}
        return DataSourceHandlerHelper.build_api_jobs(api_conf)

    def _inject_required_global_dependencies(self, global_dependencies: Dict[str, Any]) -> Dict[str, Any]:
        """
        注入全局依赖到 context。
        
        注意：scheduler 已经知道该 handler 需要哪些依赖，传入的 global_dependencies 
        只包含该 handler 需要的依赖，直接注入即可。
        
        Args:
            global_dependencies: 该 handler 需要的全局依赖字典（scheduler 已过滤）
            
        Returns:
            Dict[str, Any]: 更新后的 context（已注入依赖）
        """
        updated_context = self.context.copy()
        # 将依赖注入到 context 中（不覆盖已有键）
        for dep_name, dep_value in global_dependencies.items():
            if dep_name not in updated_context:
                updated_context[dep_name] = dep_value
        return updated_context
    
    def _add_date_range_to_api_jobs(self, context: Dict[str, Any], apis: List[ApiJob]) -> List[ApiJob]:
        """
        计算日期范围并注入到 ApiJobs 中：根据 renew_mode 自动补全日期范围。

        步骤大纲（主线逻辑）：
        1. 先检查 context 中是否已有 start_date / end_date（显式指定时原样使用，不做推断）；
        2. 调用 on_calculate_date_range 钩子，如果返回了日期范围，直接使用；
        3. 如果没有日期范围，先判断目标表是否为空：
           - 表为空：走「首次全量/初始化」路径，按配置给出一个默认日期范围（相当于 refresh 初次跑）；
        4. 如果表不为空，根据 config.renew_mode 决定增量/滚动策略：
           - incremental：从数据库中已完成的最新日期之后，增量补到当前最新周期；
           - rolling：围绕最近完成日期构造一个滚动窗口（rolling_unit + rolling_length）；
           - 其他情况（含 refresh 或未配置）：统一回退到默认日期范围策略；
        5. 将计算得到的 (start_date, end_date) 注入到每个 ApiJob 的 params 中；
        6. 返回已注入日期范围的 ApiJob 列表。

        具体的「查表 + 计算日期范围」细节下沉到 RenewManager：
        - RenewManager 作为编排层，内部委托给各种 *RenewService 做精确计算；
        - 本方法只保留步骤大纲，方便阅读主线逻辑，复杂实现不写在这里。

        复杂场景（需要特殊 renew 策略）可以在子类中覆盖 on_calculate_date_range 钩子。

        Returns:
            List[ApiJob]: 已注入日期范围的 ApiJob 列表
        """

        # 准备：构造 RenewManager（内部持有 data_manager，用于查表）
        renew_manager = RenewManager(data_manager=context.get("data_manager"))

        # 步骤 1：如果显式指定了日期范围，直接注入并返回
        if renew_manager.is_date_range_specified(context):
            start = context.get("start_date")
            end = context.get("end_date")
            return DataSourceHandlerHelper.add_date_range(apis, start, end)

        # 步骤 2：调用日期范围计算钩子（允许子类实现自定义逻辑）
        custom_date_range = self.on_calculate_date_range(context, apis)
        if custom_date_range is not None:
            # 钩子返回了日期范围，直接使用
            if isinstance(custom_date_range, dict):
                # per stock 模式
                return DataSourceHandlerHelper.add_date_range(
                    apis,
                    start_date=None,
                    end_date=None,
                    per_stock_date_ranges=custom_date_range
                )
            else:
                # 统一模式
                start, end = custom_date_range
                return DataSourceHandlerHelper.add_date_range(apis, start, end)

        # 步骤 2：判断目标表是否为空（首次全量/初始化场景）
        is_empty = renew_manager.is_table_empty(context)
        renew_mode = renew_manager.get_renew_mode(context)

        if is_empty:
            # 表为空：走首次全量/初始化路径
            start, end = renew_manager.compute_default_date_range(context)
            return DataSourceHandlerHelper.add_date_range(apis, start, end)

        if renew_mode == UpdateMode.INCREMENTAL.value:
            date_range_result = renew_manager.compute_incremental_date_range(context)
            if isinstance(date_range_result, dict):
                # per stock 模式
                return DataSourceHandlerHelper.add_date_range(
                    apis, 
                    start_date=None, 
                    end_date=None, 
                    per_stock_date_ranges=date_range_result
                )
            else:
                # 统一模式
                start, end = date_range_result
                return DataSourceHandlerHelper.add_date_range(apis, start, end)

        if renew_mode == UpdateMode.ROLLING.value and renew_manager.has_rolling_time_range(context):
            # 滚动模式：围绕最近完成日期构造滚动窗口（rolling_unit + rolling_length，内部查表）
            date_range_result = renew_manager.compute_rolling_date_range(context)
            if isinstance(date_range_result, dict):
                # per stock 模式
                return DataSourceHandlerHelper.add_date_range(
                    apis, 
                    start_date=None, 
                    end_date=None, 
                    per_stock_date_ranges=date_range_result
                )
            else:
                # 统一模式
                start, end = date_range_result
                return DataSourceHandlerHelper.add_date_range(apis, start, end)

        # 步骤 4：兜底策略（视作刷新模式，使用默认日期范围）
        start, end = renew_manager.compute_default_date_range(context)
        return DataSourceHandlerHelper.add_date_range(apis, start, end)

    def _build_api_job_batch_per_stock(self, context: Dict[str, Any], apis: List[ApiJob]) -> ApiJobBatch:
        """
        构建 job 批次：将 apis 打包成一个 batch。这个批次是per stock的。

        当前实现：将所有 apis 打包成一个 batch（对应一只股票的所有API请求）。
        未来如果需要支持多只股票并行，可以覆盖此方法，按股票拆分多个 batch。

        Args:
            context: 上下文信息
            apis: ApiJob 列表

        Returns:
            ApiJobBatch: 单个批次
        """
        if not apis:
            raise ValueError("apis 列表不能为空")

        data_source_name = context.get("data_source_name", "data_source")
        batch_id = ApiJobBatch.to_id(data_source_name)

        batch = ApiJobBatch(
            batch_id=batch_id,
            api_jobs=apis,
            description=f"{data_source_name} execution plan",
        )

        return batch

    def _execute_job_batch_for_single_stock(
        self, context: Dict[str, Any], job_batch: ApiJobBatch, all_apis: List[ApiJob]
    ) -> Dict[str, Any]:
        """
        执行单个 job batch，并在执行过程中调用单个 job 的钩子。

        Args:
            context: 上下文信息
            job_batch: 要执行的批次
            all_apis: 所有 ApiJob 列表（用于钩子调用）

        Returns:
            Dict[str, Any]: 批次执行结果 {job_id: result}
        """
        if not job_batch.api_jobs:
            return {}

        providers = context.get("providers") or {}
        executor = ApiJobExecutor(providers=providers)

        async def _run():
            # ApiJobExecutor.run_batches 返回 {batch_id: {job_id: result}}
            return await executor.run_batches([job_batch])

        # 在同步上下文中执行异步调度
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 事件循环已在运行（例如在 notebook/某些框架中），创建新的循环执行
                import threading
                result_container: Dict[str, Any] = {}

                def _worker():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        result_container["value"] = new_loop.run_until_complete(_run())
                    finally:
                        new_loop.close()

                t = threading.Thread(target=_worker)
                t.start()
                t.join()
                exec_result = result_container.get("value", {})
            else:
                exec_result = loop.run_until_complete(_run())
        except RuntimeError:
            # 当前线程没有事件循环，直接用 asyncio.run
            exec_result = asyncio.run(_run())

        # 提取批次结果
        batch_results = exec_result.get(job_batch.batch_id, {})

        # 调用单个 job 执行后的钩子（包括成功和失败的情况）
        for api_job in job_batch.api_jobs:
            # 无论成功还是失败，都调用钩子（失败时 job_result 可能是 None）
            job_result = batch_results.get(api_job.job_id)
            self.on_after_execute_single_api_job(
                self.context, api_job, {api_job.job_id: job_result}
            )

        return batch_results


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
        # 支持 DataSourceConfig 实例或 dict（兼容性）
        if hasattr(config, "get_apis"):
            apis_conf = config.get_apis()
        else:
            apis_conf = config.get("apis") if config else {}
        schema = context.get("schema")

        if not fetched_data or not isinstance(fetched_data, dict):
            # 原始数据为空或类型不对，直接返回空结果
            return {"data": []}

        # 步骤 2：做一次字段覆盖校验（提醒式，不中断执行）
        DataSourceHandlerHelper.validate_field_coverage(apis_conf, schema)

        # 步骤 3 & 4：从所有 API 返回中提取并映射出标准字段记录
        mapped_records: List[Dict[str, Any]] = DataSourceHandlerHelper.extract_mapped_records(
            apis_conf=apis_conf,
            fetched_data=fetched_data,
        )

        if not mapped_records:
            # 所有 API 都没有产生有效记录
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
        data_source_name = self.context.get("data_source_name", "unknown")
        DataSourceHandlerHelper.validate_normalized_data(normalized_data, schema, data_source_name)
        return normalized_data



    # def on_fetch(self, context: Dict[str, Any], apis: List[ApiJob]):
    #     """
    #     执行阶段：默认实现使用 TaskExecutor 执行一组 ApiJobs。

    #     步骤大纲（与原有执行逻辑保持一致）：
    #     1. 将当前 Handler 的所有 ApiJobs 打包成一个 ApiJobBatch（更语义化的执行计划批次）；
    #     2. 基于 context 中注入的 providers 构造 ApiJobExecutor（内部复用 TaskExecutor）；
    #     3. 委托 ApiJobExecutor：
    #        - 对 ApiJobs 做拓扑排序（基于 depends_on 分阶段执行）；
    #        - 收集每个 ApiJob 的限流信息，按“木桶效应”取最小值决定整体节奏；
    #        - 在每个阶段内按限流和并发策略执行所有 ApiJobs；
    #     4. 返回执行结果 {job_id: result} 字典。
    #     """
        # if not apis:
        #     return {}

        # data_source_name = context.get("data_source_name")
        # batch_id = ApiJobBatch.to_id(data_source_name)

        # # 1. 构造语义化的 ApiJobBatch（对外暴露的执行计划概念）
        # batch = ApiJobBatch(
        #     batch_id=batch_id,
        #     api_jobs=apis,
        #     description=f"{data_source_name} execution plan",
        # )

        # providers = context.get("providers") or {}
        # scheduler = ApiJobScheduler(providers=providers)

        # async def _run():
        #     # ApiJobScheduler.run_batches 返回 {batch_id: {job_id: result}}
        #     return await scheduler.run_batches([batch])

        # # 在同步上下文中执行异步调度
        # import asyncio

        # try:
        #     loop = asyncio.get_event_loop()
        #     if loop.is_running():
        #         # 事件循环已在运行（例如在 notebook/某些框架中），创建新的循环执行
        #         import threading
        #         result_container: Dict[str, Any] = {}

        #         def _worker():
        #             new_loop = asyncio.new_event_loop()
        #             asyncio.set_event_loop(new_loop)
        #             try:
        #                 result_container["value"] = new_loop.run_until_complete(_run())
        #             finally:
        #                 new_loop.close()

        #         t = threading.Thread(target=_worker)
        #         t.start()
        #         t.join()
        #         exec_result = result_container.get("value", {})
        #     else:
        #         exec_result = loop.run_until_complete(_run())
        # except RuntimeError:
        #     # 当前线程没有事件循环，直接用 asyncio.run
        #     exec_result = asyncio.run(_run())

        # return exec_result.get(batch_id, {})

    # ================================
    # Hooks
    # ================================

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

    def on_after_build_job_batch_for_single_stock(self, context: Dict[str, Any], job_batch: ApiJobBatch) -> ApiJobBatch:
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
        return job_batch

    def on_after_execute_single_api_job(self, context: Dict[str, Any], api_job: ApiJob, fetched_data: Dict[str, Any]):
        """
        执行单个 api job 后的钩子。
        """
        pass

    def on_after_execute_job_batch_for_single_stock(self, context: Dict[str, Any],job_batch: ApiJobBatch, fetched_data: Dict[str, Any]):
        """
        执行 job batch 后的钩子。
        """
        pass

    def on_after_fetch(self, context: Dict[str, Any], fetched_data: Dict[str, Any], apis: List[ApiJob]):
        """
        抓取完成后的预处理钩子（标准化之前）。

        常见用途：
        - 记录抓取统计信息；
        - 对多路数据结果做合并/清洗；
        - 为标准化阶段补充必要的上下文信息。

        默认行为：直接返回 fetched_data。
        """
        return fetched_data

    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]):
        # 可重写，有默认行为：默认直接返回 normalized_data
        return normalized_data

    def on_error(self, error: Exception, context: Dict[str, Any], apis: List[ApiJob]) -> None:
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
        data_source_name = context.get("data_source_name", "unknown")
        logger.error(f"❌ 数据源 {data_source_name} 执行失败: {error}")