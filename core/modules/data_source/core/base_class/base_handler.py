"""
BaseHandler - 数据源 Handler 基类。

模块加载时即禁用 tqdm，避免 akshare 等依赖的进度条与我们的日志混在一起。
"""
import os
os.environ["TQDM_DISABLE"] = "1"  # 强制禁用，避免 akshare 等依赖的进度条混入日志

from typing import Any, Dict, List, Tuple, Optional
import logging
import time

from core.modules.data_source.core.base_class.base_provider import BaseProvider
from core.modules.data_source.core.service.handler_helper import DataSourceHandlerHelper
from core.modules.data_source.core.data_class.api_job import ApiJob
from core.modules.data_source.core.data_class.api_job_bundle import ApiJobBundle
from core.modules.data_source.core.data_class.config import DataSourceConfig
from core.modules.data_source.core.enums import UpdateMode
from core.modules.data_manager import DataManager

from core.modules.data_source.core.hooks.base import DataSourceHooks


logger = logging.getLogger(__name__)


def format_run_seconds(seconds: float) -> str:
    """进度日志用的耗时。不足 10 秒保留一位小数。"""
    seconds = max(0.0, float(seconds))
    if seconds < 10:
        text = f"{seconds:.1f}".rstrip("0").rstrip(".")
        return f"{text}s"
    return f"{int(round(seconds))}s"


def _is_official_sync(config: Any) -> bool:
    """这一份数据源只从官网续传自己绑定的那张表。"""
    if not isinstance(config, DataSourceConfig):
        return False
    apis = list(config.get_apis().values())
    if len(apis) != 1:
        return False
    api = apis[0]
    return api.provider_name == "ntq" and api.method == "sync"


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
        hooks: Optional["DataSourceHooks"] = None,
    ):
        if depend_on_data_source_names is None:
            depend_on_data_source_names = []
        self.context = {
            "data_source_key": data_source_key,
            "schema": schema,
            "config": config,
            "providers": providers,
            "data_manager": DataManager.get_instance(),
            "depend_on_data_source_names": depend_on_data_source_names,
        }
        self.hooks = hooks if hooks is not None else DataSourceHooks()
        self.hooks.bind(self)
        from core.modules.data_source.core.progress import SyncProgress
        self.progress = SyncProgress(str(data_source_key or "data_source"))
        self.context["_progress"] = self.progress

    # ================================
    # Getters
    # ================================

    def get_key(self) -> Optional[str]:
        """数据源配置键（mapping 中的 key，用于串联 config、dependencies 等），与 DB 表名无关。"""
        return self.context.get("data_source_key")

    def get_dependency_data_source_names(self) -> List[str]:
        """获取依赖的数据源名称列表"""
        return self.context.get("depend_on_data_source_names", [])

    def renew_mode_label(self, *, force: bool = False) -> str:
        """本次实际执行模式。force 覆盖配置，按全量重拉。"""
        if force:
            return UpdateMode.REFRESH.value
        config = self.context.get("config")
        if config is None:
            return ""
        mode = config.get_renew_mode()
        if isinstance(mode, UpdateMode):
            return mode.value
        return str(mode or "")

    def _remember_run_timing(self, started: float, plan_done: float) -> None:
        now = time.perf_counter()
        plan = max(0.0, plan_done - started)
        execute = max(0.0, now - plan_done)
        self._last_run_timing = {
            "plan": plan,
            "execute": execute,
            "total": plan + execute,
        }

    def _print_plan_elapsed(self, seconds: float) -> None:
        print(f"任务规划耗时：{format_run_seconds(seconds)}", flush=True)

    # ================================
    # Main entrance: execute
    # ================================
    def execute(self, dependencies_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handler 的同步执行入口（默认实现）。

        流程大纲：
        0. on_before_run 返回非 None 则直接结束；官网同步按本表的 renew 计算区间后再翻页；
        1. _preprocess：预处理阶段（构建 ApiJobs、计算日期范围、调用 on_before_fetch 钩子）；
        2. _executing：执行阶段（构建批次、执行 API 请求、调用 on_after_fetch 钩子）；
        3. _postprocess：后处理阶段（标准化数据、调用 on_after_normalize 钩子、数据验证）；
        4. _do_save：非 is_dry_run 时先调用 on_before_save（用户可返回替代数据），再系统写入绑定表；
        5. 返回标准化后的数据。
        """
        started = time.perf_counter()
        self.context["_bundle_errors"] = []
        self.context["_bundle_error_count"] = 0
        self._inject_dependencies(dependencies_data)
        config = self.context.get("config")
        self.context["is_dry_run"] = config.get_is_dry_run() if config else False

        early_result = self.hooks.on_before_run(self.context)
        if early_result is not None:
            plan_done = time.perf_counter()
            self._print_plan_elapsed(plan_done - started)
            self._remember_run_timing(started, plan_done)
            return early_result

        jobs = self._preprocess(dependencies_data)
        plan_done = time.perf_counter()
        self._print_plan_elapsed(plan_done - started)

        if _is_official_sync(config):
            from core.modules.data_source.core.service.official_sync import pull_table

            saved = pull_table(self, jobs)
            self._remember_run_timing(started, plan_done)
            # 行已经写入绑定表。data 留给调度器登记“这个源跑过了”，下游不再按股票拆任务。
            return {"saved": saved, "data": []}

        fetched_data = self._executing(jobs)

        normalized_data = self._postprocess(fetched_data)

        normalized_data = self._do_save(normalized_data)

        self._remember_run_timing(started, plan_done)
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
        data_source_key = self.get_key()
        is_dry_run = self.context.get("is_dry_run", False)
        dry_run_status = " [DRY RUN]" if is_dry_run else ""
        logger.debug(f"[{data_source_key}] 开始预处理阶段{dry_run_status}")

        # 1. 上下文准备
        self.hooks.on_prepare_context(self.context)

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

        jobs = self.hooks.on_before_fetch(self.context, jobs)
        
        data_source_key = self.get_key()
        is_dry_run = self.context.get("is_dry_run", False)
        dry_run_status = " [DRY RUN]" if is_dry_run else ""
        logger.debug(f"[{data_source_key}] 预处理完成: {len(jobs)} 个 job bundles{dry_run_status}")

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
                return DataManager.sample_universe.slice_stock_list(entity_list or [])

            # 回退到 dependencies
            deps = self.context.get("dependencies") or {}
            entity_list = deps.get("stock_list")
            if entity_list is None:
                return []
            return DataManager.sample_universe.slice_stock_list(entity_list or [])
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
        from core.modules.data_source.core.service.date_range.date_range_service import DateRangeService

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
        from core.modules.data_source.core.service.date_range.date_range_service import DateRangeService

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
        然后调用钩子 on_after_build_jobs。
        """
        from core.modules.data_source.core.service.job.job_builder import JobBuilder

        entity_list = self._get_entity_list()
        builder = JobBuilder()

        jobs = builder.build_jobs(
            context=self.context,
            apis_conf=apis_conf,
            entity_list=entity_list,
            entity_date_ranges=entity_date_ranges,
            build_single_job=self._build_job,
        )

        jobs = self.hooks.on_after_build_jobs(self.context, jobs, entity_date_ranges)

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

        from core.modules.data_source.core.data_class.config import DataSourceConfig

        start_date, end_date = date_range
        config = self.context.get("config")
        if not isinstance(config, DataSourceConfig):
            config = None

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

        # 按 params_mapping 注入实体字段（如 ts_code/symbol <- id），再由 on_build_job_payload 做格式转换
        if entity_info is not None:
            group_fields = config.get_group_fields() if config else []
            entity_key_field = (
                group_fields[0]
                if group_fields
                else (config.get_group_by_key() if config else "id")
            )
            DataSourceHandlerHelper.apply_entity_params_mapping(
                entity_info, apis, apis_conf, entity_key_field or "id"
            )

        # per-entity 场景：构建 job payload（使用钩子方法，允许子类自定义如何提取实体 ID 并注入参数）
        entity_id = self.hooks.on_build_job_payload(entity_info, apis, self.context)

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
        deps = dependencies_data if dependencies_data is not None else {}
        deps = DataManager.sample_universe.slice_stock_list_in_dependencies(deps)
        self.context["dependencies"] = deps
        exec_meta = deps.get("_execution")
        self.context["force_refresh"] = (
            bool(exec_meta.get("force_refresh"))
            if isinstance(exec_meta, dict)
            else False
        )
        # 从保留依赖 latest_completed_trading_date 提取日期写入 context
        if dependencies_data and "latest_completed_trading_date" in dependencies_data:
            val = dependencies_data["latest_completed_trading_date"]
            if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict) and "date" in val[0]:
                self.context["latest_completed_trading_date"] = val[0]["date"]

    # ================================
    # Executing stage
    # ================================
    def _executing(self, apis_job_bundles: List[ApiJob]) -> Dict[str, Any]:
        """执行任务并汇总。每个任务结束时由引擎写出进度。"""
        from core.modules.data_source.core.service.pipeline.runner import (
            DataSourcePipelineRunner,
        )

        try:
            self.context["_bundle_to_frames"] = self.hooks.bundle_to_frames
            self.context["_save_frames"] = self.hooks.save_frames
            fetched_data = DataSourcePipelineRunner().run_bundles(
                self.context,
                apis_job_bundles,
                enrich_result_for_batch=self.hooks.enrich_result_for_batch,
            )

            # 将执行的 apis 扁平化注入 context，供 on_after_fetch 使用
            all_apis: List[ApiJob] = []
            for item in apis_job_bundles or []:
                if isinstance(item, ApiJobBundle):
                    all_apis.extend(item.apis or [])
                elif isinstance(item, ApiJob):
                    all_apis.append(item)

            fetched_data = self.hooks.on_after_fetch(self.context, fetched_data, all_apis)

            return fetched_data
        except Exception as e:
            # 步骤 6：错误处理
            self.hooks.on_bundle_execution_error(e, self.context, apis_job_bundles)
            raise

    # ================================
    # Postprocess stage
    # ================================
    def _postprocess(self, fetched_data: Any) -> Dict[str, Any]:
        logger.debug(
            "[_postprocess] fetched_data keys: %s",
            list(fetched_data.keys())[:5] if isinstance(fetched_data, dict) else "N/A",
        )
        
        # 调用 normalize_data（子类可以覆盖此方法）
        normalized_data = self.normalize_data(self.context, fetched_data)
        logger.debug(
            "[_postprocess] normalize_data 完成，条数: %s",
            len(normalized_data.get("data", [])) if isinstance(normalized_data, dict) else 0,
        )

        normalized_data = self.hooks.on_after_normalize(self.context, normalized_data)

        normalized_data = self._validate_normalized_data(normalized_data)

        return normalized_data

    def _normalize_data(self, context: Dict[str, Any], fetched_data: Any):
        """标准化阶段默认实现。

        交给 NormalizationService 做字段映射和日期标准化，再调用 on_after_mapping，最后套用表 schema。
        """
        from core.modules.data_source.core.service.normalization.normalization_service import NormalizationService
        from core.modules.data_source.core.service.normalization import normalization_helper as nh

        if not fetched_data:
            return {"data": []}

        # 使用 NormalizationService 完成公共标准化流程（字段映射 / schema 等）
        # 注意：NormalizatonService 内部已经做了字段覆盖校验、日期标准化等。
        normalized = NormalizationService.normalize(context, fetched_data)

        # NormalizationService 返回 {"data": [...]}。拆出记录交给 on_after_mapping，再套用表 schema。
        data_list = normalized.get("data") if isinstance(normalized, dict) else None
        if not data_list:
            return {"data": []}

        # 在 mapping 之后、套用 schema 之前调用 hook。
        mapped_records = self.hooks.on_after_mapping(context, data_list)
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
        from core.modules.data_source.core.service.normalization import normalization_helper as nh

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
        
        抓取过程中已经按缓冲区写入时，这里不再写第二次。
        返回值仍交给调度器；被下游依赖的源可以据此缓存 data。
        """
        if self.context.get("buffer_persisted"):
            logger.debug("[_do_save] 缓冲区已写入，跳过收尾保存")
            return normalized_data

        config = self.context.get("config")
        if not config:
            raise ValueError("缺少 config")
        data_list = normalized_data.get("data", []) if isinstance(normalized_data, dict) else []
        if not data_list:
            return normalized_data
        
        logger.debug(
            "[_do_save] 保存 %s 条",
            len(normalized_data.get("data", [])) if isinstance(normalized_data, dict) else 0,
        )
        if self._is_dry_run():
            logger.debug("[_do_save] dry run，跳过保存")
            return normalized_data
        resolved = self.hooks.on_before_save(self.context, normalized_data)
        data_to_save = resolved if resolved is not None else normalized_data
        self._system_save(data_to_save)
        return data_to_save

    def _system_save(self, normalized_data: Dict[str, Any]) -> None:
        """
        将标准化数据写入绑定表（使用表 schema 的 primaryKey 做 upsert）。
        仅框架内部调用；用户自定义写入请在 on_before_save 中实现。
        """
        from core.modules.data_source.core.service.persistence.persistence_service import PersistenceService

        PersistenceService.save(self.context, normalized_data)

    # ================================
    # Hooks
    # ================================

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

    def _bundle_to_frames(self, context: Dict[str, Any], job_bundle: Any, fetched_data: Dict[str, Any]):
        """把一笔抓取结果变成映射后的表。原始返回不进入缓冲区。"""
        import pandas as pd

        rows = self._extract_normalized_rows_for_bundle(context, job_bundle, fetched_data)
        if not rows:
            return []
        return [pd.DataFrame(rows)]

    def _save_record_chunk(self, context: Dict[str, Any], rows: List[Dict[str, Any]]) -> None:
        """写入固定行数的记录。子类可改成自己的保存函数。"""
        if not rows or context.get("is_dry_run"):
            return
        self._system_save({"data": rows})

    def _save_frames(self, context: Dict[str, Any], frames: List[Any]) -> None:
        """按固定行数把多张表写成记录，不把整个缓冲区合成一张表或一份字典。"""
        from core.modules.data_source.core.service.pipeline.frame_mapping import (
            WRITE_CHUNK_ROWS,
            records_from_frame,
        )

        if context.get("is_dry_run") or not frames:
            return
        pending: List[Dict[str, Any]] = []

        def flush_pending() -> None:
            if not pending:
                return
            rows = list(pending)
            pending.clear()
            self.hooks.save_record_chunk(context, rows)

        for frame in frames:
            if frame is None or getattr(frame, "empty", True):
                continue
            total = len(frame)
            for start in range(0, total, WRITE_CHUNK_ROWS):
                pending.extend(records_from_frame(frame.iloc[start : start + WRITE_CHUNK_ROWS]))
                if len(pending) >= WRITE_CHUNK_ROWS:
                    flush_pending()
        flush_pending()

    def _extract_normalized_rows_for_bundle(
        self,
        context: Dict[str, Any],
        job_bundle: Any,
        fetched_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """从单个 bundle 抓取结果提取待写入行（供 batch 合并）。子类可覆盖。"""
        apis = self._apis_for_save_bundle(job_bundle)
        if not apis or not isinstance(fetched_data, dict):
            return []
        partial = {k: v for k, v in fetched_data.items() if v is not None}
        if not partial:
            return []
        unified = self.hooks.on_after_fetch(context, partial, apis)
        normalized = self._normalize_data(context, unified)
        return list(normalized.get("data") or [])

    @staticmethod
    def _apis_for_save_bundle(job_bundle: Any) -> List[ApiJob]:
        if isinstance(job_bundle, ApiJob):
            return [job_bundle]
        if isinstance(job_bundle, ApiJobBundle):
            return list(job_bundle.apis or [])
        return []
