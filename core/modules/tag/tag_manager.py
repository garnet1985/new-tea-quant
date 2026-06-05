"""
Tag Manager - 统一管理所有业务场景（Scenario）

负责发现、验证和执行所有 scenario workers。
"""
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Type, Any, Tuple, Union
import logging
from pathlib import Path
from core.modules.tag.enums import TagTargetType, TagUpdateMode
from core.modules.tag.base_tag_worker import BaseTagWorker
from core.modules.tag.components.helper.tag_helper import TagHelper
from core.modules.tag.components.helper.job_helper import JobHelper
from core.modules.data_manager import DataManager
from core.modules.data_contract.cache import ContractCacheManager
from core.modules.data_contract.contract_const import ContractScope, DataKey
from core.modules.data_contract.data_contract_manager import DataContractManager
from core.modules.tag.config import get_scenarios_root
from core.infra.project_context import PathManager
from core.modules.tag.enums import FileName
from core.modules.tag.models.scenario_model import ScenarioModel
from core.infra.job_pipeline import (
    DispatchResult,
    ExecuteMode,
    ExecutionBackend,
    Job,
    JobContext,
    JobPipeline,
    JobPipelineSettings,
    JobReport,
    RunProgress,
)
from core.infra.job_pipeline.profile.probe import WorkerProbe
from core.infra.job_pipeline.profile import (
    WorkerProfiles,
    profile_max_parallel_jobs_cap,
    profile_reserve_cores,
)
from core.infra.worker.dispatch_planner import resolve_dispatch_plan
from core.modules.tag.components.tag_dispatch_probe import (
    DEFAULT_PROBE_ENTITIES,
    run_tag_dispatch_probe,
    should_run_dispatch_probe,
)
from core.modules.tag.components.job_staging.tag_run_profile import TagRunProfile
from core.modules.tag.components.report_save_buffer import TagReportSaveBuffer
from core.infra.db.engines.duckdb.wal_policy import should_checkpoint_after_tag_run

logger = logging.getLogger(__name__)

# DEBUG：dispatcher 调试期间限制实体数量；None = 全量
_DEBUG_ENTITY_LIMIT: Optional[int] = None
# DEBUG：覆盖 entities_per_job；None 则用 performance 或 DEFAULT_ENTITIES_PER_JOB
_DEBUG_ENTITIES_PER_JOB: Optional[int] = None
class TagManager:
    """Tag Manager - 统一管理所有业务场景"""
    
    def __init__(self, is_verbose=False, dispatch_overrides: Optional[Dict[str, Any]] = None):
        """初始化 TagManager"""
        self.is_verbose = is_verbose
        self._dispatch_overrides = dict(dispatch_overrides or {})
        self.data_mgr = DataManager()
        self.tag_data_service = self.data_mgr.stock.tags
        self._contract_cache = ContractCacheManager()
        self._data_contract_manager = DataContractManager(contract_cache=self._contract_cache)
        self.scenario_cache = {}
        self.entity_list_cache = {}
        self._discover_scenarios_from_folder()

    @staticmethod
    def _resolve_worker_amount(max_workers: Any) -> int:
        """已废弃：并行度由 JobPipelineSettings / WorkerProbe 解析。"""
        from core.infra.job_pipeline.profile.probe import WorkerProbe

        return WorkerProbe.resolve(max_workers if max_workers is not None else "auto")

    def refresh_scenario(self):
        self._clear_cache()
        self._discover_scenarios_from_folder()

    def execute(self, scenario_name: str = None, settings: Dict[str, Any] = None):
        if settings:
            self._execute_single_from_tmp_settings(settings)
        elif scenario_name:  
            self._execute_single(scenario_name)
        else:
            self._execute_all()
        # 注意：不清空缓存，因为缓存中的 worker_module_path 等信息在子进程中需要用到
        # self._clear_cache()

    # -------------------------------------------------------------------------
    # Scenario 执行
    # -------------------------------------------------------------------------

    def _execute_single_from_tmp_settings(self, settings: Dict[str, Any]):
        scenario_model = ScenarioModel.create_from_settings(settings)
        if not scenario_model:
            logger.info(f"创建场景模型失败，跳过执行")
            return
 
        self._run_execute_pipeline(scenario_model)

    def _execute_single(self, scenario_name: str):
        """
        执行单个 scenario（从缓存加载）
        
        Args:
            scenario_name: Scenario 名称
        """
        scenario_cache = self._load_scenario_from_cache_by_name(scenario_name)
        if not scenario_cache:
            logger.info(f"找不到场景名: {scenario_name}，跳过执行")
            return
        
        # ScenarioModel.create_from_settings 需要完整的 settings 字典（包含 "scenario" 和 "tags"）
        settings = scenario_cache.get("settings", {})
        scenario_model = ScenarioModel.create_from_settings(settings)
        if not scenario_model:
            return

        self._run_execute_pipeline(scenario_model)

    def _execute_all(self):
        for scenario_name in self.scenario_cache:
            self._execute_single(scenario_name)


    # -------------------------------------------------------------------------
    # Scenario 发现与加载
    # -------------------------------------------------------------------------

    def _discover_scenarios_from_folder(self):
        """发现并缓存所有 scenario settings"""
        scenario_cache = {}
        root_folder = get_scenarios_root()
        
        if not root_folder.exists():
            logger.warning(f"Tag scenarios 根目录不存在: {root_folder}")
            self.scenario_cache = {}
            return

        for scenario_folder in root_folder.iterdir():
            if not scenario_folder.is_dir() or scenario_folder.name.startswith('_'):
                continue

            cache_item = self._build_scenario_cache(scenario_folder)
            if not cache_item:
                continue      

            scenario_cache[cache_item["name"]] = cache_item
            if self.is_verbose:
                logger.info(f"发现可用场景: {cache_item['name']}, 文件夹: {scenario_folder.name}")
        
        self.scenario_cache = scenario_cache

    def _build_scenario_cache(self, scenario_folder: Path):
        settings_path, settings_dict = TagHelper.load_scenario_settings(scenario_folder)
        if not settings_path:
            self.is_verbose and logger.warning(f"文件夹 {scenario_folder.name} 下找不到 {FileName.SETTINGS.value} 文件，跳过。")
            return None
        worker_class_path, worker_class = TagHelper.load_worker_class(scenario_folder)
        if not worker_class_path:
            self.is_verbose and logger.warning(f"文件夹 {scenario_folder.name} 下找不到 {FileName.TAG_WORKER.value} 文件，跳过。")
            return None

        if not settings_dict:
            self.is_verbose and logger.warning(f"文件夹 {scenario_folder.name} 下的 {FileName.SETTINGS.value} 文件内容无效，跳过。")
            return None
        if not worker_class:
            self.is_verbose and logger.warning(f"文件夹 {scenario_folder.name} 下的 {FileName.TAG_WORKER.value} 文件内容无效，跳过。")
            return None

        # 新结构：name 直接在顶层，不在 scenario 子字典中
        scenario_name = settings_dict.get("name")
        if not scenario_name:
            self.is_verbose and logger.warning(f"文件夹 {scenario_folder.name} 下的 {FileName.SETTINGS.value} 文件中缺少 name 字段，跳过。")
            return None

        logger.debug(f"发现场景: {worker_class_path}, 文件夹: {scenario_folder.name}")

        # 获取 worker_class 的模块路径和类名（用于子进程重新导入，避免 pickle 问题）
        worker_class_name = worker_class.__name__
        # 构建完整的模块路径（相对于项目根目录）
        # 例如：userspace/extensions/tags/momentum/tag_worker.py -> userspace.extensions.tags.momentum.tag_worker
        worker_module_full_path = self._calculate_module_path(worker_class_path)

        return {
            "name": scenario_name,
            "scenario_folder_path": scenario_folder.name,
            "settings": settings_dict,
            "settings_file_path": settings_path,
            "worker_class": worker_class,  # 保留用于非多进程场景
            "worker_file_path": worker_class_path,
            "worker_module_path": worker_module_full_path,  # 用于子进程重新导入
            "worker_class_name": worker_class_name,  # 用于子进程重新导入
        }

    def _load_scenario_from_cache_by_name(self, name: str):
        """从缓存中加载 scenario"""
        return self.scenario_cache.get(name)
    
    def _calculate_module_path(self, file_path: Path) -> str:
        """
        计算文件路径对应的模块路径
        
        Args:
            file_path: 文件路径（如 userspace/extensions/tags/momentum/tag_worker.py）
            
        Returns:
            模块路径（如 userspace.extensions.tags.momentum.tag_worker）
        """
        try:
            # 相对于项目根目录计算
            root = PathManager.get_root()
            relative_path = file_path.resolve().relative_to(root.resolve())
            # 转换为模块路径：去掉.py后缀，替换路径分隔符为点
            module_path = str(relative_path.with_suffix('')).replace('/', '.').replace('\\', '.')
            return module_path
        except (ValueError, AttributeError):
            # 如果无法计算相对路径，使用文件名作为后备
            logger.warning(f"无法计算模块路径: {file_path}，使用文件名作为后备")
            return file_path.stem

    def _get_entity_list(self, scenario_model: ScenarioModel) -> List[str]:
        """
        获取实体列表
        
        Args:
            scenario_model: ScenarioModel 实例
            
        Returns:
            List[str]: 实体ID列表
        """
        settings = scenario_model.get_settings()
        declarations = (settings.get("data") or {}).get("required") or []
        per_entity_data_id = self._pick_primary_per_entity_data_id(declarations)
        if per_entity_data_id is None:
            logger.warning("当前场景无 PER_ENTITY 数据源，无法构建 entity 列表")
            return []

        cache_key = f"per_entity:{per_entity_data_id}"
        if cache_key in self.entity_list_cache:
            return self.entity_list_cache[cache_key]

        spec = self._data_contract_manager.map.get(per_entity_data_id) or {}
        list_data_id = spec.get("entity_list_data_id")
        if not isinstance(list_data_id, DataKey):
            logger.warning(
                "data_id=%s 未注册 entity_list_data_id，无法推导实体列表",
                per_entity_data_id.value,
            )
            return []
        list_contract = self._data_contract_manager.issue(list_data_id).require_contract()
        list_rows = list(list_contract.data or [])
        list_spec = self._data_contract_manager.map.get(list_data_id) or {}
        keys = list_spec.get("unique_keys") or ["id"]
        id_field = str(keys[0]) if keys else "id"
        entity_list = [row.get(id_field) for row in list_rows if row.get(id_field)]

        self.entity_list_cache[cache_key] = entity_list
        return entity_list

    def _pick_primary_per_entity_data_id(self, declarations: List[Dict[str, Any]]) -> Optional[DataKey]:
        for item in declarations:
            raw = str(item.get("data_id") or "").strip()
            if not raw:
                continue
            try:
                dk = DataKey(raw)
            except ValueError:
                continue
            spec = self._data_contract_manager.map.get(dk)
            if spec and spec.get("scope") == ContractScope.PER_ENTITY:
                return dk
        return None

    def _get_worker_class(self, scenario_name: str, scenario_model: ScenarioModel) -> Optional[Type[BaseTagWorker]]:
        """
        获取 worker_class
        
        优先从 cache 中获取，如果不在 cache 中，尝试从 scenario_model 的 settings 中加载
        
        Args:
            scenario_name: Scenario 名称
            scenario_model: ScenarioModel 实例
            
        Returns:
            Optional[Type[BaseTagWorker]]: Worker 类，如果获取失败返回 None
        """
        # 优先从 cache 中获取
        if scenario_name in self.scenario_cache:
            return self.scenario_cache[scenario_name].get("worker_class")
        
        # 如果不在 cache 中（例如从 _execute_single_from_tmp_settings 进入），返回 None
        # 注意：通常 scenario 应该通过 execute() 方法执行，会自动加载到 cache
        logger.warning(f"Scenario {scenario_name} 不在 cache 中，无法获取 worker_class")
        return None

    def _clear_cache(self):
        self.scenario_cache = {}
        self.entity_list_cache = {}



    # -------------------------------------------------------------------------
    # Scenario job 构建与执行
    # -------------------------------------------------------------------------


    def _run_execute_pipeline(self, scenario_model: ScenarioModel):
        """
        执行 scenario 的完整流程
        
        Args:
            scenario_model: ScenarioModel 实例
        """
        # 检查场景是否启用
        if not scenario_model.is_enabled():
            logger.info(f"场景 {scenario_model.get_name()} 未开启（is_enabled=False）, 跳过执行")
            return

        # 获取 tag_data_service 并确保元信息存在
        tag_data_service = self.data_mgr.stock.tags
        if not tag_data_service:
            logger.error(f"无法获取 tag_data_service，跳过执行")
            return
        scenario_model.ensure_metadata(tag_data_service)

        settings = scenario_model.get_settings()
        performance = dict(settings.get("performance") or {})
        performance.update(self._dispatch_overrides)
        execute_mode = self._parse_execute_mode(performance.get("execute_mode"))
        if execute_mode == ExecuteMode.ELASTIC:
            raise NotImplementedError("ExecuteMode.ELASTIC is not implemented yet")

        tag_target_type = str(settings.get("tag_target_type") or TagTargetType.ENTITY_BASED.value).strip().lower()
        # 获取实体列表
        if tag_target_type == TagTargetType.GENERAL.value:
            entity_list = ["__general__"]
        else:
            entity_list = self._get_entity_list(scenario_model)
        if not entity_list:
            logger.info(f"无法获取实体列表，跳过执行")
            return

        stock_limit = self._dispatch_overrides.get("stock_limit")
        if stock_limit is None:
            stock_limit = _DEBUG_ENTITY_LIMIT
        if stock_limit is not None and len(entity_list) > int(stock_limit):
            logger.warning(
                "实体列表截断 %d → %d（stock_limit）",
                len(entity_list),
                int(stock_limit),
            )
            entity_list = entity_list[: int(stock_limit)]

        # 获取 worker_class（从 cache 中获取，如果不在 cache 中则尝试从 settings 加载）
        scenario_name = scenario_model.get_name()
        worker_class = self._get_worker_class(scenario_name, scenario_model)
        if not worker_class:
            logger.error(f"无法获取 worker_class，跳过执行: scenario={scenario_name}")
            return

        # 获取更新模式

        # 调试：在调用 _build_jobs 前检查缓存
        if self.is_verbose:
            logger.debug(f"🔍 _run_execute_pipeline: 准备构建 jobs")
            logger.debug(f"   scenario_name: {scenario_name}")
            logger.debug(f"   scenario_cache exists: {scenario_name in self.scenario_cache}")
            if scenario_name in self.scenario_cache:
                logger.debug(f"   Cache has worker_module_path: {'worker_module_path' in self.scenario_cache[scenario_name]}")

        performance = dict(settings.get("performance") or {})
        performance.update(self._dispatch_overrides)
        measured_mb: Optional[float] = None
        ep_explicit = (
            _DEBUG_ENTITIES_PER_JOB is not None
            or performance.get("entities_per_job") not in (None, "", "auto")
        )
        if should_run_dispatch_probe(
            performance,
            total_entities=len(entity_list),
            entities_per_job_explicit=ep_explicit,
        ):
            probe_n = max(
                1,
                min(
                    int(performance.get("dispatch_probe_entities", DEFAULT_PROBE_ENTITIES)),
                    len(entity_list),
                ),
            )
            probe_jobs = self._build_jobs(
                entity_list,
                settings,
                scenario_model,
                worker_class,
                entities_per_job=probe_n,
                log_job_grouping=False,
            )
            if probe_jobs and probe_jobs[0].get("payload"):
                logger.info(
                    "[%s] Tag 调度探针: 子进程试跑 %d 股（与生产相同 stage+算）…",
                    scenario_name,
                    probe_n,
                )
                payload = dict(probe_jobs[0]["payload"])
                payload["_run_name"] = f"tag:{scenario_name}"
                try:
                    from core.infra.db.engines.duckdb.process_pool_scope import (
                        duckdb_worker_pool_main_process,
                    )

                    with duckdb_worker_pool_main_process(
                        self.data_mgr,
                        resume_main_after=False,
                        wait_children_timeout_sec=15.0,
                    ):
                        probe_result = run_tag_dispatch_probe(
                            payload,
                            performance=performance,
                        )
                        measured_mb = probe_result.mb_per_entity
                except Exception as exc:
                    logger.warning(
                        "Tag 调度探针失败，回退默认 mb 估算: %s",
                        exc,
                    )
        if self._backend_is_duckdb(self.data_mgr) and getattr(
            self.data_mgr, "db", None
        ) is None:
            from core.infra.db.engines.duckdb.process_pool_scope import (
                resume_main_database_with_retry,
            )

            resume_main_database_with_retry(self.data_mgr)
            self.tag_data_service = self.data_mgr.stock.tags
        dispatch_plan = resolve_dispatch_plan(
            total_entities=len(entity_list),
            performance=performance,
            log_label="Tag",
            debug_entities_per_job=_DEBUG_ENTITIES_PER_JOB,
            measured_mb_per_entity=measured_mb,
            worker_profile=WorkerProfiles.TAG,
        )
        performance["max_workers"] = dispatch_plan.max_workers
        performance["prefetch_ahead"] = dispatch_plan.prefetch_ahead
        jobs = self._build_jobs(
            entity_list,
            settings,
            scenario_model,
            worker_class,
            entities_per_job=dispatch_plan.entities_per_job,
        )

        if not jobs:
            logger.warning(f"没有新的计算任务，跳过执行: scenario={scenario_name}")
            return

        self._execute_jobs(
            jobs,
            scenario_name,
            worker_class,
            performance=performance,
            profile_enabled=bool(
                self.is_verbose
                or performance.get("profile")
                or os.environ.get("NTQ_TAG_PROFILE", "").strip() in ("1", "true", "yes")
            ),
        )

    def _build_jobs(
        self,
        entity_list: List[str],
        settings: Dict[str, Any],
        scenario_model: ScenarioModel,
        worker_class: Type[BaseTagWorker],
        *,
        entities_per_job: int = 1,
        log_job_grouping: bool = True,
    ):
        """
        构建 jobs（每个 entity 一个 job）
        
        针对当前 scenario，为每个 entity 构建一个 job。
        对于 INCREMENTAL 模式，需要查询该 scenario 下所有 tag values 的最近记录，找到每个 entity 的最大 as_of_date。
        
        Args:
            entity_list: 实体ID列表
            settings: Settings 字典
            scenario_model: ScenarioModel 实例
            worker_class: Worker 类
        """
        update_mode = scenario_model.calculate_update_mode()
        scenario_name = scenario_model.get_name()

        # 获取默认日期
        default_start_date = settings.get("start_date")
        default_end_date = settings.get("end_date")
        
        # 获取实体类型（从 scenario_model 获取）
        tag_target_type = str(settings.get("tag_target_type") or TagTargetType.ENTITY_BASED.value).strip().lower()
        entity_type = "general" if tag_target_type == TagTargetType.GENERAL.value else scenario_model.get_target_entity()
        
        # 获取 tag definitions 列表（从 scenario_model 获取）
        tag_models = scenario_model.get_tag_models()
        tag_definitions = [tag_model.to_dict() for tag_model in tag_models]
        
        # 如果是 INCREMENTAL 模式，需要获取该 scenario 下所有 tag values 的最近记录
        # 查询逻辑：找到该 scenario 下所有 tag_definition_ids 对应的 tag_value 记录，
        # 按 entity_id 分组，找到每个 entity 的最大 as_of_date
        entity_last_update_info = {}
        if update_mode == TagUpdateMode.INCREMENTAL:
            # 获取该 scenario 下所有 entity 的最后更新信息
            # 返回格式：{entity_id: {"max_as_of_date": "20250101", ...}, ...}
            tag_data_service = self.data_mgr.stock.tags
            if tag_data_service:
                entity_last_update_info = tag_data_service.get_tag_value_last_update_info(scenario_name)
        
        jobs = []
        global_extra_cache = self._build_global_extra_cache(settings, start=default_start_date, end=default_end_date)
        latest_completed = JobHelper._resolve_latest_completed_trading_date()
        entity_specs: List[Dict[str, Any]] = []

        scenario_cache = self.scenario_cache.get(scenario_name)
        if not scenario_cache:
            raise ValueError(f"Scenario {scenario_name} 不在缓存中")
        worker_module_path = scenario_cache.get("worker_module_path")
        worker_class_name = scenario_cache.get("worker_class_name")
        if not worker_module_path or not worker_class_name:
            raise ValueError(
                f"缺少 worker 模块信息: worker_module_path={worker_module_path}, "
                f"worker_class_name={worker_class_name}"
            )

        for entity_id in entity_list:
            entity_last_update_date = None
            if update_mode == TagUpdateMode.INCREMENTAL:
                entity_info = entity_last_update_info.get(entity_id, {})
                entity_last_update_date = entity_info.get("max_as_of_date")

            start_date, end_date = JobHelper.calculate_start_and_end_date(
                update_mode=update_mode,
                entity_last_update_date=entity_last_update_date,
                default_start_date=default_start_date,
                default_end_date=default_end_date,
                latest_completed_trading_date=latest_completed,
            )

            entity_specs.append(
                {
                    "entity_id": entity_id,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )

        shared_payload = {
            "entity_type": entity_type,
            "scenario_name": scenario_name,
            "update_mode": update_mode,
            "tag_definitions": tag_definitions,
            "settings": settings,
            "worker_module_path": worker_module_path,
            "worker_class_name": worker_class_name,
            "global_extra_cache": global_extra_cache,
        }
        batch_size = max(1, int(entities_per_job))
        scenario_id = scenario_model.get_identifier()
        for batch_idx in range(0, len(entity_specs), batch_size):
            batch = entity_specs[batch_idx : batch_idx + batch_size]
            if batch_size == 1:
                ent = batch[0]
                job_id = f"{scenario_id}_{ent['entity_id']}"
                jobs.append(
                    {
                        "id": job_id,
                        "payload": {**shared_payload, **ent, "_job_id": job_id},
                    }
                )
            else:
                job_id = f"{scenario_id}_batch{batch_idx // batch_size}"
                jobs.append(
                    {
                        "id": job_id,
                        "payload": {**shared_payload, "entities": batch, "_job_id": job_id},
                    }
                )

        if log_job_grouping:
            logger.info(
                "Tag jobs 分组: entities=%d, entities_per_job=%d, dispatch_jobs=%d",
                len(entity_specs),
                batch_size,
                len(jobs),
            )
        if log_job_grouping and batch_size == 1 and len(entity_specs) > 100:
            logger.warning(
                "entities_per_job=1：约 %d 次 dispatch，wall 通常 ~60s；"
                "建议 performance.entities_per_job=100（子进程 bulk stage 才有效）",
                len(jobs),
            )

        return jobs

    @staticmethod
    def _configured_database_type(data_mgr: Optional[DataManager] = None) -> str:
        """库类型：优先已连接 db；suspend 后从 userspace 配置读取。"""
        db = getattr(data_mgr, "db", None) if data_mgr else None
        if db is not None:
            return str(db.config.get("database_type") or "").lower()
        from core.infra.project_context import ConfigManager

        return str(ConfigManager.load_database_config().get("database_type") or "").lower()

    @staticmethod
    def _backend_is_duckdb(data_mgr: DataManager) -> bool:
        return TagManager._configured_database_type(data_mgr) == "duckdb"

    @staticmethod
    def _parse_execute_mode(raw: Any) -> ExecuteMode:
        try:
            return ExecuteMode(str(raw or "queue").lower())
        except ValueError:
            return ExecuteMode.QUEUE

    def _execute_jobs(
        self,
        jobs: List[Dict[str, Any]],
        scenario_name: str,
        worker_class: Type[BaseTagWorker],
        *,
        performance: Optional[Dict[str, Any]] = None,
        profile_enabled: bool = False,
    ):
        performance = performance or {}
        stage_in_worker = performance.get("stage_in_worker", True)
        if isinstance(stage_in_worker, str):
            stage_in_worker = stage_in_worker.strip().lower() in ("1", "true", "yes")
        else:
            stage_in_worker = bool(stage_in_worker)
        if os.environ.get("NTQ_TAG_STAGE_IN_WORKER", "").strip().lower() in (
            "1",
            "true",
            "yes",
        ):
            stage_in_worker = True
        duckdb_stage_spill = stage_in_worker and self._backend_is_duckdb(self.data_mgr)
        save_batch_size = int(performance.get("save_batch_size", 5000))
        dispatch_settings = JobPipelineSettings(
            worker=ExecutionBackend.PROCESS,
            execute_mode=self._parse_execute_mode(performance.get("execute_mode")),
            max_workers=performance.get("max_workers", "auto"),
            batch_size=int(performance.get("batch_size", 10)),
            prefetch_ahead=int(performance.get("prefetch_ahead", 1)),
            worker_profile=WorkerProfiles.TAG,
            duckdb_process_pool_scope="auto",
            duckdb_data_mgr=self.data_mgr,
            duckdb_resume_main_after_pool=not duckdb_stage_spill,
        )
        run_name = f"tag:{scenario_name}"
        total_jobs = len(jobs)
        entity_count = sum(
            len(j["payload"].get("entities") or [{"entity_id": j["payload"].get("entity_id")}])
            for j in jobs
            if j.get("payload")
        )
        start_time = time.time()
        profile = TagRunProfile(enabled=profile_enabled)
        for job in jobs:
            if job.get("payload") and stage_in_worker:
                job["payload"]["_stage_in_worker"] = True

        tag_data_service_ref = self.tag_data_service
        real_save_fn = tag_data_service_ref.save_batch
        spill_dir: Optional[Path] = None
        if duckdb_stage_spill:
            spill_rows = int(performance.get("stage_spill_rows") or 50_000)
            spill_dir = Path(
                tempfile.mkdtemp(prefix=f"ntq_tag_{scenario_name}_")
            )
            save_buffer = TagReportSaveBuffer(
                real_save_fn,
                batch_size=save_batch_size,
                accumulate_only=True,
                spill_row_threshold=spill_rows,
                spill_dir=spill_dir,
            )
        else:
            save_buffer = TagReportSaveBuffer(
                real_save_fn,
                batch_size=save_batch_size,
            )
        progress_state = {"last_pct": -1, "finished": 0}

        def on_result(report: JobReport, progress: RunProgress) -> None:
            t0 = time.perf_counter()
            save_batch_sec = 0.0
            if not report.success:
                logger.error(
                    "Tag job 失败: job_id=%s error=%s",
                    report.job_id,
                    report.error,
                )
            else:
                data = report.data if isinstance(report.data, dict) else {}
                stage_sec = data.get("_profile_stage_sec")
                if isinstance(stage_sec, (int, float)):
                    profile.record_stage(
                        elapsed_sec=float(stage_sec),
                        payload=data.get("_stage_payload_hint") or {},
                    )
                exec_sec = data.get("_profile_execute_sec")
                if isinstance(exec_sec, (int, float)):
                    profile.record_execute(float(exec_sec))
                tag_values = data.get("tag_values") or []
                if tag_values:
                    save_batch_sec = save_buffer.extend_in_chunks(tag_values)

            profile.record_report(
                elapsed_sec=time.perf_counter() - t0,
                save_batch_sec=save_batch_sec,
            )

            progress_state["finished"] = progress.finished
            finished = progress_state["finished"]
            pct = int(finished * 100 / total_jobs) if total_jobs else 100
            if finished == total_jobs or pct >= progress_state["last_pct"] + 5:
                logger.info(
                    "[%s] Tag 进度: %s/%s (%s%%) 成功=%s 失败=%s",
                    run_name,
                    finished,
                    total_jobs,
                    pct,
                    progress.ok,
                    progress.fail,
                )
                progress_state["last_pct"] = pct

        dispatcher_jobs = [Job(job_id=job["id"], payload=job["payload"]) for job in jobs]
        resolved_workers = WorkerProbe.resolve(
            dispatch_settings.max_workers,
            reserve_cores=profile_reserve_cores(WorkerProfiles.TAG),
            cap=profile_max_parallel_jobs_cap(WorkerProfiles.TAG),
        )
        logger.info(
            "[%s] 🚀 开始执行 dispatch_jobs=%s entities=%s (workers=%s, max_workers=%r, "
            "reserve_cores=%s, mode=%s, stage_in_worker=%s)",
            run_name,
            total_jobs,
            entity_count,
            resolved_workers,
            dispatch_settings.max_workers,
            dispatch_settings.reserve_cores,
            dispatch_settings.execute_mode.value,
            stage_in_worker,
        )

        dispatch_result = DispatchResult(total=total_jobs, run_name=run_name)
        interrupted = False
        spill_rows = int(performance.get("stage_spill_rows") or 50_000)
        duckdb_worker_pool = duckdb_stage_spill
        try:
            dispatch_result = self._run_tag_dispatch(
                dispatcher_jobs=dispatcher_jobs,
                dispatch_settings=dispatch_settings,
                on_result=on_result,
                run_name=run_name,
                stage_in_worker=stage_in_worker,
                duckdb_spill=duckdb_stage_spill,
                spill_rows=spill_rows,
            )
            if dispatch_result.failed and dispatch_result.failures:
                for item in dispatch_result.failures[:5]:
                    logger.error(
                        "Dispatch failure: job_id=%s phase=%s error=%s",
                        item.job_id,
                        getattr(item.phase, "value", item.phase),
                        item.error,
                    )
        except KeyboardInterrupt:
            interrupted = True
            logger.warning(
                "[%s] 用户中断 (Ctrl+C)：等待 worker 退出后 flush 已攒批数据…",
                run_name,
            )
            raise
        finally:
            if duckdb_stage_spill:
                logger.info("[%s] ⏳ 等待 tag 数据写入完成…", run_name)
                from core.infra.db.engines.duckdb.process_pool_scope import (
                    resume_main_database_with_retry,
                )
                from core.modules.tag.components.job_staging.worker_runtime import (
                    digest_stage_in_worker_save_buffer,
                )

                try:
                    save_sec = digest_stage_in_worker_save_buffer(
                        self.data_mgr,
                        save_buffer,
                        batch_size=save_batch_size,
                    )
                    if save_sec > 0:
                        logger.info(
                            "[%s] DuckDB 收尾写库 %.2fs（%s 行，spills=%s）",
                            run_name,
                            save_sec,
                            save_buffer.saved_row_count,
                            save_buffer.spill_count,
                        )
                    resume_main_database_with_retry(self.data_mgr)
                    self.tag_data_service = self.data_mgr.stock.tags
                except Exception as exc:
                    logger.warning("[%s] stage 收尾失败: %s", run_name, exc)
                save_buffer.cleanup_spill_dir()
            else:
                logger.info("[%s] ⏳ 等待 tag 数据写入完成…", run_name)
                try:
                    save_buffer.flush()
                except Exception as exc:
                    logger.warning("[%s] 收尾 flush 失败: %s", run_name, exc)
            db = getattr(self.data_mgr, "db", None) if self.data_mgr else None
            if db is not None:
                try:
                    db.wait_for_writes(timeout=60.0 if not interrupted else 15.0)
                    logger.info("[%s] ✅ tag 数据写入完成", run_name)
                    self._maybe_checkpoint_duckdb_after_tag_run()
                except Exception as exc:
                    logger.warning("[%s] 等待写入或 CHECKPOINT 失败: %s", run_name, exc)

        completed_jobs = dispatch_result.completed
        failed_jobs = dispatch_result.failed
        elapsed_time = time.time() - start_time
        saved_tag_count = save_buffer.saved_row_count

        logger.info(
            f"Tag计算完成: scenario={scenario_name}, "
            f"dispatch_jobs={total_jobs}, entities={entity_count}, "
            f"成功={completed_jobs}, 失败={failed_jobs}, "
            f"写入tag_values={saved_tag_count}, "
            f"save_batch次数={save_buffer.flush_count}, 耗时={elapsed_time:.2f}秒"
        )
        db_type = ""
        if self.data_mgr:
            db_type = self._configured_database_type(self.data_mgr)
        for line in profile.summary_lines(total_jobs=total_jobs, database_type=db_type):
            logger.info(line)

        return {
            "scenario_name": scenario_name,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "saved_tag_values": saved_tag_count,
            "elapsed_time": elapsed_time,
            "dispatch_result": dispatch_result,
        }

    def _run_tag_dispatch(
        self,
        *,
        dispatcher_jobs: List[Job],
        dispatch_settings: JobPipelineSettings,
        on_result,
        run_name: str,
        stage_in_worker: bool,
        duckdb_spill: bool,
        spill_rows: int,
    ) -> DispatchResult:
        """单次 JobPipeline.run；子进程 execute 内 stage+算，DuckDB 锁由 JobPipeline + process_pool_scope 协作。"""
        if stage_in_worker and duckdb_spill:
            logger.info(
                "[%s] stage_in_worker + DuckDB spill（buffer≥%d 行 Parquet，池结束后写 tag）",
                run_name,
                spill_rows,
            )
        elif stage_in_worker:
            logger.info(
                "[%s] stage_in_worker（%s：on_result 攒批直接 save_batch）",
                run_name,
                self._configured_database_type(self.data_mgr),
            )
        dispatcher = JobPipeline(
            settings=dispatch_settings,
            execute=TagManager._execute_single_job,
            on_result=on_result,
        )
        return dispatcher.run(dispatcher_jobs, run_name=run_name)

    def _maybe_checkpoint_duckdb_after_tag_run(self) -> None:
        """DuckDB：Tag 写库结束后合并 WAL，避免下次启动回放失败。"""
        db = getattr(self.data_mgr, "db", None) if self.data_mgr else None
        if db is None or str(db.config.get("database_type") or "").lower() != "duckdb":
            return
        if not should_checkpoint_after_tag_run(db.config):
            return
        try:
            results = db.checkpoint_duckdb()
            if not results:
                return
            failed = [d for d, ok in results.items() if not ok]
            ok_domains = sorted(d for d, ok in results.items() if ok)
            if failed:
                logger.warning(
                    "DuckDB WAL 合并未完成: 失败 domain=%s；成功=%s。"
                    "（写队列忙时可重试 dev-cli.py -dbc --recover）",
                    failed,
                    ok_domains,
                )
            else:
                logger.info("DuckDB WAL 已合并（domains=%s）", ok_domains)
        except Exception as exc:
            logger.warning(
                "Tag 完成后 CHECKPOINT 异常（若下次启动报 WAL: python dev-cli.py -dbc --recover）: %s",
                exc,
            )

    def _build_global_extra_cache(
        self,
        settings: Dict[str, Any],
        *,
        start: Optional[str],
        end: Optional[str],
    ) -> Dict[str, List[Dict[str, Any]]]:
        data_block = settings.get("data")
        if not isinstance(data_block, dict):
            return {}
        if not start or not end:
            return {}

        declarations = data_block.get("required") or []
        if not isinstance(declarations, list):
            return {}
        out: Dict[str, List[Dict[str, Any]]] = {}
        for item in declarations:
            data_id = str(item.get("data_id") or "").strip()
            if not data_id:
                continue
            dk = DataKey(data_id)
            spec = self._data_contract_manager.map.get(dk)
            if not spec:
                continue
            if spec.get("scope") != ContractScope.GLOBAL:
                continue
            params = dict(item.get("params") or {})
            c = self._data_contract_manager.issue(
                dk,
                start=start,
                end=end,
                **params,
            ).require_contract()
            out[dk.value] = list(c.data or [])
        return out

    @staticmethod
    def _maybe_stage_in_worker(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
        from core.modules.tag.components.job_staging.worker_runtime import (
            payload_needs_worker_stage,
            stage_payload_in_worker,
        )

        if not payload_needs_worker_stage(payload):
            return payload, 0.0
        stage_t0 = time.perf_counter()
        staged = stage_payload_in_worker(payload)
        return staged, time.perf_counter() - stage_t0

    @staticmethod
    def _execute_single_job(context: JobContext) -> Dict[str, Any]:
        """
        Tag Worker（JobPipeline execute）：子进程内 stage（可选）+ 计算。

        主进程 on_result 负责 save_batch；load 数据由本函数与 worker_runtime 完成。
        """
        payload = context.payload
        stage_in_worker = bool(payload.get("_stage_in_worker"))
        try:
            payload, stage_sec = TagManager._maybe_stage_in_worker(payload)
            entities = payload.get("entities")
            if isinstance(entities, list) and len(entities) > 1:
                out = TagManager._execute_batch_entities(payload, entities)
                if stage_sec > 0:
                    out["_profile_stage_sec"] = stage_sec
                return out

            exec_t0 = time.perf_counter()
            try:
                result = TagManager._run_worker_for_payload(payload)
                execute_sec = time.perf_counter() - exec_t0
                out = {
                    "success": bool(result.get("success", True)),
                    "entity_id": payload.get("entity_id"),
                    "tag_values": result.get("tag_values") or [],
                    "total_tags": result.get("total_tags_created", 0),
                    "processed_dates": result.get("processed_dates", 0),
                    "total_dates": result.get("total_dates", 0),
                    "errors": result.get("errors") or [],
                    "_profile_execute_sec": execute_sec,
                }
                if stage_sec > 0:
                    out["_profile_stage_sec"] = stage_sec
                return out
            except Exception as e:
                logger.exception(
                    "Job %s failed: %s", payload.get("entity_id", "unknown"), e
                )
                out = {
                    "success": False,
                    "entity_id": payload.get("entity_id"),
                    "tag_values": [],
                    "error": str(e),
                    "_profile_execute_sec": time.perf_counter() - exec_t0,
                }
                if stage_sec > 0:
                    out["_profile_stage_sec"] = stage_sec
                return out
        finally:
            if stage_in_worker:
                from core.modules.tag.components.job_staging.worker_runtime import (
                    release_worker_runtime,
                )

                release_worker_runtime()

    @staticmethod
    def _execute_batch_entities(
        payload: Dict[str, Any],
        entities: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        exec_t0 = time.perf_counter()
        inject_root = payload.get("_inject") or {}
        by_entity = inject_root.get("by_entity") or {}
        all_tag_values: List[Dict[str, Any]] = []
        errors: List[str] = []
        ok = True

        for ent in entities:
            eid = str(ent.get("entity_id") or "")
            slice_inject = by_entity.get(eid)
            if slice_inject is None:
                ok = False
                errors.append(f"missing inject slice for entity_id={eid}")
                continue
            sub_payload = TagManager._entity_sub_payload(payload, ent, slice_inject)
            try:
                result = TagManager._run_worker_for_payload(sub_payload)
                if not result.get("success", True):
                    ok = False
                all_tag_values.extend(result.get("tag_values") or [])
                errors.extend(result.get("errors") or [])
            except Exception as exc:
                ok = False
                msg = f"entity_id={eid}: {exc}"
                logger.exception("Batch job entity failed: %s", msg)
                errors.append(msg)

        return {
            "success": ok,
            "entity_count": len(entities),
            "tag_values": all_tag_values,
            "total_tags": len(all_tag_values),
            "errors": errors,
            "_profile_execute_sec": time.perf_counter() - exec_t0,
        }

    @staticmethod
    def _entity_sub_payload(
        payload: Dict[str, Any],
        entity: Dict[str, Any],
        inject_slice: Dict[str, Any],
    ) -> Dict[str, Any]:
        keys = (
            "entity_type",
            "scenario_name",
            "update_mode",
            "tag_definitions",
            "settings",
            "worker_module_path",
            "worker_class_name",
            "global_extra_cache",
        )
        sub = {key: payload[key] for key in keys if key in payload}
        sub.update(entity)
        sub["_inject"] = inject_slice
        return sub

    @staticmethod
    def _run_worker_for_payload(job_payload: Dict[str, Any]) -> Dict[str, Any]:
        import importlib

        worker_module_path = job_payload.get("worker_module_path")
        worker_class_name = job_payload.get("worker_class_name")
        if not worker_module_path or not worker_class_name:
            raise ValueError(
                f"缺少 worker 模块信息: worker_module_path={worker_module_path}, "
                f"worker_class_name={worker_class_name}"
            )
        worker_module = importlib.import_module(worker_module_path)
        worker_class = getattr(worker_module, worker_class_name)
        worker = worker_class(job_payload=job_payload)
        return worker.process_entity()

