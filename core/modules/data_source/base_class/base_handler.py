"""
BaseHandler - 数据源 Handler 基类。

模块加载时即禁用 tqdm，避免 akshare 等依赖的进度条与我们的日志混在一起。
"""
import os
os.environ["TQDM_DISABLE"] = "1"  # 强制禁用，避免 akshare 等依赖的进度条混入日志

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
        self.context["is_dry_run"] = config.get_is_dry_run() if config else False

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
        # compute_entity_date_ranges 在 last_update_map 为空时会单独查 gate 并注入 context，优先使用
        self.context["_last_update_map"] = self.context.get("_last_update_map") or last_update_map
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
        获取 per-entity 的实体列表。仅当 job_execution.list == "stock_list" 时从
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
            # 其他 list 名（如 index_list）：从 dependencies 或 context 获取，由 handler 在 on_prepare_context 中注入
            deps = self.context.get("dependencies") or {}
            entity_list = deps.get(group_by_entity_list_name) or self.context.get(group_by_entity_list_name)
            return (entity_list or []) if entity_list is not None else []
        return []

    def _get_last_update_map(self) -> Dict[str, Optional[str]]:
        """
        Phase 1：获取所有实体的“原始” last_update 映射（不考虑 renew_mode）。
        具体 DB 查询与标准化逻辑委托给 DateRangeService（内部目前仍转调 DataSourceHandlerHelper）。
        """
        from core.modules.data_source.service.date_range.date_range_service import DateRangeService

        service = DateRangeService()
        return service.compute_last_update_map(self.context)

    def _calculate_entity_date_ranges(
        self, last_update_map: Dict[str, Optional[str]]
    ) -> Dict[str, Tuple[str, str]]:
        """
        Phase 2：基于 last_update 映射 + renew_mode + renew_if_over_days，
        计算本次需要抓取的实体及其 (start_date, end_date)。

        实际计算逻辑委托给 DateRangeService（内部目前仍转调 DataSourceHandlerHelper），
        这里保留骨架，方便子类在必要时覆写。
        """
        from core.modules.data_source.service.date_range.date_range_service import DateRangeService

        service = DateRangeService()
        return service.compute_entity_date_ranges(self.context, last_update_map)

    def _build_jobs(
        self,
        apis_conf: Dict[str, Any],
        entity_date_ranges: Dict[str, Tuple[str, str]],
    ) -> List[ApiJobBundle]:
        """
        基于 entity_date_ranges 构建 ApiJobBundle 列表。
        
        当前实现委托给 JobBuilder 完成实体维度的遍历和单个实体 Job 的构建，
        然后在 BaseHandler 层调用 on_after_build_jobs 做二次处理（保持与旧行为一致）。
        """
        from core.modules.data_source.service.job.job_builder import JobBuilder

        entity_list = self._get_entity_list()
        builder = JobBuilder()

        jobs = builder.build_jobs(
            context=self.context,
            apis_conf=apis_conf,
            entity_list=entity_list,
            entity_date_ranges=entity_date_ranges,
            build_single_job=self._build_job,
        )

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

        # per-entity 场景：使用同一套实体 ID 约定（config.job_execution.key）
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
        from core.modules.data_source.service.executor.bundle_execution_service import (
            BundleExecutionService,
        )

        try:
            executor = BundleExecutionService()
            fetched_data = executor.execute(
                self.context,
                apis_job_bundles,
                on_after_single_bundle_complete=self.on_after_single_api_job_bundle_complete,
                enrich_result_for_batch=self.enrich_result_for_batch,
            )

            # 将执行的 apis 扁平化注入 context，供 on_after_fetch 使用
            all_apis: List[ApiJob] = []
            for item in apis_job_bundles or []:
                if isinstance(item, ApiJobBundle):
                    all_apis.extend(item.apis or [])
                elif isinstance(item, ApiJob):
                    all_apis.append(item)

            fetched_data = self.on_after_fetch(self.context, fetched_data, all_apis)

            return fetched_data
        except Exception as e:
            # 步骤 6：错误处理
            self.on_bundle_execution_error(e, self.context, apis_job_bundles)
            raise

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
        标准化阶段默认实现。
        
        为兼容现有行为，内部委托给 NormalizationService 完成公共标准化流程，
        再在 BaseHandler 层调用 on_after_mapping 钩子。
        """
        from core.modules.data_source.service.normalization.normalization_service import NormalizationService
        from core.modules.data_source.service.normalization import normalization_helper as nh

        if not fetched_data:
            return {"data": []}

        # 使用 NormalizationService 完成公共标准化流程（字段映射 / schema 等）
        # 注意：NormalizatonService 内部已经做了字段覆盖校验、日期标准化等。
        normalized = NormalizationService.normalize(context, fetched_data)

        # NormalizationService 已经返回 {"data": [...]} 结构；为了保持与旧实现兼容，
        # 在这里拆出 records，交给 on_after_mapping 进行二次处理后再重新 apply_schema。
        data_list = normalized.get("data") if isinstance(normalized, dict) else None
        if not data_list:
            return {"data": []}

        # 在 mapping 后、schema 应用前调用 hook（行为与旧实现保持一致）
        mapped_records = self.on_after_mapping(context, data_list)
        if not mapped_records:
            return {"data": []}

        schema = context.get("schema")
        normalized_records = nh.apply_schema(mapped_records, schema)
        return nh.build_normalized_payload(normalized_records)

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
        from core.modules.data_source.service.normalization import normalization_helper as nh

        nh.validate_normalized_data(
            normalized_data,
            schema,
            data_source_key,
            ignore_fields=ignore_fields,
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
        if not config:
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
        from core.modules.data_source.service.persistence.persistence_service import PersistenceService

        PersistenceService.save(self.context, normalized_data)

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
            entity_key_field: 实体键字段名（来自 config.job_execution.key，通常是 "id"）
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
        group_fields = config.get_group_fields() if config else []
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

    def enrich_result_for_batch(self, context: Dict[str, Any], job_bundle: Any, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        在 batch 模式检查 _has_actual_data 之前，允许子类丰富 result，使空结果也包含元数据（如 last_update）。
        需要复权的：复权信息 + update 时间；不需要复权的：update 时间。这样 actual data 恒非空。
        默认返回原 result 不变。
        """
        return raw_result

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
        抓取完成后的钩子：将 {job_id: result} 转为 {api_name: {entity_id: result}}，
        供 normalize 阶段的 extract_mapped_records 使用。

        默认行为：根据 has_group_by_config 选择：
        - 有 job_execution 且 apis 含 params_mapping：build_grouped_fetched_data，按实体分组；
        - 否则：build_unified_fetched_data，按 api_name 聚合到 "_unified"。
        """
        from core.modules.data_source.service.executor import fetched_data_helper as fd

        if fd.has_group_by_config(context, apis):
            return fd.build_grouped_fetched_data(context, fetched_data, apis)
        return fd.build_unified_fetched_data(context, fetched_data, apis)

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
            mapped_records: 已应用 result_mapping 的记录列表

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

        内部委托 record_utils 和 DBHelper 实现，子类无需关心具体细节。
        """
        from core.modules.data_source.service.utils import record_utils

        return record_utils.clean_nan_in_records(records, default=default)

    @staticmethod   
    def clean_nan_in_normalized_data(normalized_data: Dict[str, Any], default: Any = None) -> Dict[str, Any]:
        """
        针对标准化结果的便捷 NaN 清洗：
        - 如果 normalized_data 是 {"data": [...]}，则对 data 列表做清洗；
        - 否则尝试直接将 normalized_data 视为单条记录列表的一部分。
        """
        from core.modules.data_source.service.utils import record_utils

        return record_utils.clean_nan_in_normalized_data(normalized_data, default=default)

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
        from core.modules.data_source.service.utils import record_utils

        return record_utils.filter_records_by_required_fields(records, required_fields)

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
        from core.modules.data_source.service.utils import record_utils

        return record_utils.ensure_float_field(records, field, default=default)
