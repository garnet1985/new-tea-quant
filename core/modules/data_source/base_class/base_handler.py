from typing import Any, Dict, List

from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper
from core.modules.data_source.service.api_job_scheduler import ApiJobScheduler
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.data_class.api_job_batch import ApiJobBatch
from core.modules.data_source.data_class.config import DataSourceConfig
from core.modules.data_source.data_class.schema import DataSourceSchema
from core.modules.data_source.data_classes import DataSourceTask


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
        }
        self.apis: List[ApiJob] = self._config_to_api_jobs()
        self.fetched_data: Dict[str, Any] = {}
        self.normalized_data: Dict[str, Any] = {}

    def execute(self) -> Dict[str, Any]:
        """
        Handler 的同步执行入口（默认实现）。

        流程大纲：
        1. 重置内部状态；
        2. on_before_fetch：允许子类基于 context 调整 ApiJobs（例如补参数、拆分等）；
        3. on_fetch：默认使用调度器/执行器执行 ApiJobs（包含拓扑排序、限流、并发调度），返回原始数据；
        4. on_after_fetch：提供在标准化前对原始数据做预处理的扩展点；
        5. on_normalize：将原始数据按 schema 标准化；
        6. on_after_normalize：后处理钩子；
        7. 返回标准化后的数据。
        """
        self._reset()

        apis = self.on_before_fetch(self.context, self.apis)
        self.fetched_data = self.on_fetch(self.context, apis)
        self.fetched_data = self.on_after_fetch(self.context, self.fetched_data, apis)
        self.normalized_data = self.on_normalize(self.context, self.fetched_data)
        self.normalized_data = self.on_after_normalize(self.context, self.normalized_data)

        return self.normalized_data


    def _config_to_api_jobs(self) -> List[ApiJob]:
        """
        第一步：将 config 中声明的 apis 转换为 ApiJob 列表。

        职责：
        - 这里只负责描述“要调用哪些 API”，不关心如何执行和限流；
        - 具体转换规则由 DataSourceHandlerHelper.build_api_jobs 负责。
        """
        api_conf = self.context.get("config").get("apis")
        return DataSourceHandlerHelper.build_api_jobs(api_conf)

    def _reset(self):
        self.fetched_data = None
        self.normalized_data = None


    # ================================
    # Hooks
    # ================================

    def on_before_fetch(self, context: Dict[str, Any], apis: List[ApiJob]):
        # 可重写，有默认行为：默认直接返回 apis
        return apis

    def on_fetch(self, context: Dict[str, Any], apis: List[ApiJob]):
        """
        执行阶段：默认实现使用 TaskExecutor 执行一组 ApiJobs。

        步骤大纲（与原有执行逻辑保持一致）：
        1. 将当前 Handler 的所有 ApiJobs 打包成一个 ApiJobBatch（更语义化的执行计划批次）；
        2. 基于 context 中注入的 providers 构造 ApiJobExecutor（内部复用 TaskExecutor）；
        3. 委托 ApiJobExecutor：
           - 对 ApiJobs 做拓扑排序（基于 depends_on 分阶段执行）；
           - 收集每个 ApiJob 的限流信息，按“木桶效应”取最小值决定整体节奏；
           - 在每个阶段内按限流和并发策略执行所有 ApiJobs；
        4. 返回执行结果 {job_id: result} 字典。
        """
        if not apis:
            return {}

        data_source_name = context.get("data_source_name")
        batch_id = ApiJobBatch.to_id(data_source_name)

        # 1. 构造语义化的 ApiJobBatch（对外暴露的执行计划概念）
        batch = ApiJobBatch(
            batch_id=batch_id,
            api_jobs=apis,
            description=f"{data_source_name} execution plan",
        )

        providers = context.get("providers") or {}
        scheduler = ApiJobScheduler(providers=providers)

        async def _run():
            # ApiJobScheduler.run_batches 返回 {batch_id: {job_id: result}}
            return await scheduler.run_batches([batch])

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

        return exec_result.get(batch_id, {})

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

    def on_normalize(self, context: Dict[str, Any], fetched_data: Dict[str, Any]):
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
        config: Dict[str, Any] = context.get("config") or {}
        apis_conf: Dict[str, Any] = config.get("apis") or {}
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

    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]):
        # 可重写，有默认行为：默认直接返回 normalized_data
        return normalized_data