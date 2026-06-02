"""
Tag Manager - 统一管理所有业务场景（Scenario）

负责发现、验证和执行所有 scenario workers。
"""
import os
import time
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
from core.infra.job_dispatcher import (
    ExecutionBackend,
    JobDispatcher,
    JobReport,
    JobShell,
    StagedJob,
    create_job_executor,
)
from core.modules.tag.components.job_staging.tag_job_stager import TagJobStager
from core.modules.tag.components.job_staging.tag_run_profile import TagRunProfile
from core.modules.tag.components.report_save_buffer import TagReportSaveBuffer
from core.infra.db.engines.duckdb.wal_policy import should_checkpoint_after_tag_run

logger = logging.getLogger(__name__)

class TagManager:
    """Tag Manager - 统一管理所有业务场景"""
    
    def __init__(self, is_verbose = False):
        """初始化 TagManager"""
        self.is_verbose = is_verbose
        self.data_mgr = DataManager()
        self.tag_data_service = self.data_mgr.stock.tags
        self._contract_cache = ContractCacheManager()
        self._data_contract_manager = DataContractManager(contract_cache=self._contract_cache)
        self.scenario_cache = {}
        self.entity_list_cache = {}
        self._discover_scenarios_from_folder()

    @staticmethod
    def _resolve_worker_amount(max_workers: Any) -> int:
        """解析 worker 数量配置，保证返回 >=1 的整数。"""
        if max_workers == "auto" or max_workers is None:
            return os.cpu_count() or 10
        try:
            return max(1, int(max_workers))
        except Exception:
            return os.cpu_count() or 10

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
        list_contract = self._data_contract_manager.issue(list_data_id)
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
        tag_target_type = str(settings.get("tag_target_type") or TagTargetType.ENTITY_BASED.value).strip().lower()
        # 获取实体列表
        if tag_target_type == TagTargetType.GENERAL.value:
            entity_list = ["__general__"]
        else:
            entity_list = self._get_entity_list(scenario_model)
        if not entity_list:
            logger.info(f"无法获取实体列表，跳过执行")
            return
        
        # 测试模式：只使用前2个实体进行测试（如果启用）
        # 注意：这个测试逻辑应该通过配置控制，而不是硬编码
        # TODO: 通过 settings 或 context 控制测试模式

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

        jobs = self._build_jobs(entity_list, settings, scenario_model, worker_class)

        if not jobs:
            logger.warning(f"没有新的计算任务，跳过执行: scenario={scenario_name}")
            return

        # 执行 jobs
        # 从 settings 中获取 max_workers 配置
        performance = settings.get("performance", {})
        max_workers = performance.get("max_workers", "auto")
        profile_enabled = bool(
            self.is_verbose
            or performance.get("profile")
            or os.environ.get("NTQ_TAG_PROFILE", "").strip() in ("1", "true", "yes")
        )
        save_batch_size = int(performance.get("save_batch_size", 5000))
        self._execute_jobs(
            jobs,
            scenario_name,
            worker_class,
            max_workers=max_workers,
            profile_enabled=profile_enabled,
            save_batch_size=save_batch_size,
        )

    def _build_jobs(self, entity_list: List[str], settings: Dict[str, Any], scenario_model: ScenarioModel, worker_class: Type[BaseTagWorker]):
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
        
        # 调试：检查缓存状态（强制输出，不依赖 is_verbose）
        logger.info(f"🔍 _build_jobs: 开始构建 jobs for scenario: {scenario_name}")
        logger.info(f"   scenario_cache exists: {scenario_name in self.scenario_cache}")
        logger.info(f"   All cached scenarios: {list(self.scenario_cache.keys())}")
        if scenario_name in self.scenario_cache:
            cache_keys = list(self.scenario_cache[scenario_name].keys())
            logger.info(f"   Cache keys for {scenario_name}: {cache_keys}")
            logger.info(f"   worker_module_path in cache: {'worker_module_path' in self.scenario_cache[scenario_name]}")
            logger.info(f"   worker_class_name in cache: {'worker_class_name' in self.scenario_cache[scenario_name]}")
            if 'worker_module_path' in self.scenario_cache[scenario_name]:
                logger.info(f"   worker_module_path value: {self.scenario_cache[scenario_name].get('worker_module_path')}")
            if 'worker_class_name' in self.scenario_cache[scenario_name]:
                logger.info(f"   worker_class_name value: {self.scenario_cache[scenario_name].get('worker_class_name')}")
        else:
            logger.error(f"   ❌ Scenario {scenario_name} 不在缓存中!")
        
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

        for entity_id in entity_list:
            # 获取该 entity 的最后更新日期（INCREMENTAL 模式）
            # 从该 scenario 下所有 tag values 中找到该 entity 的最大 as_of_date
            entity_last_update_date = None
            if update_mode == TagUpdateMode.INCREMENTAL:
                entity_info = entity_last_update_info.get(entity_id, {})
                entity_last_update_date = entity_info.get("max_as_of_date")
            
            # 计算该 entity 的 start_date 和 end_date
            start_date, end_date = JobHelper.calculate_start_and_end_date(
                update_mode=update_mode,
                entity_last_update_date=entity_last_update_date,
                default_start_date=default_start_date,
                default_end_date=default_end_date
            )
            
            # 从 cache 获取 worker 模块信息（用于子进程重新导入）
            # 注意：每次循环都要重新获取，确保获取到最新的缓存
            scenario_cache = self.scenario_cache.get(scenario_name)
            if not scenario_cache:
                logger.error(f"❌ Scenario {scenario_name} 不在缓存中!")
                logger.error(f"   Available scenarios: {list(self.scenario_cache.keys())}")
                logger.error(f"   scenario_cache type: {type(self.scenario_cache)}")
                logger.error(f"   scenario_cache content: {self.scenario_cache}")
                raise ValueError(f"Scenario {scenario_name} 不在缓存中")
            
            worker_module_path = scenario_cache.get("worker_module_path")
            worker_class_name = scenario_cache.get("worker_class_name")
            
            # 调试：如果值为 None，记录详细警告
            if not worker_module_path or not worker_class_name:
                logger.error(f"❌ Scenario {scenario_name} 的缓存中缺少 worker 模块信息!")
                logger.error(f"   worker_module_path={worker_module_path}")
                logger.error(f"   worker_class_name={worker_class_name}")
                logger.error(f"   scenario_cache type: {type(scenario_cache)}")
                logger.error(f"   scenario_cache keys: {list(scenario_cache.keys()) if isinstance(scenario_cache, dict) else 'Not a dict'}")
                logger.error(f"   scenario_cache full content: {scenario_cache}")
                logger.error(f"   Available scenarios: {list(self.scenario_cache.keys())}")
                raise ValueError(f"缺少 worker 模块信息: worker_module_path={worker_module_path}, worker_class_name={worker_class_name}")
            
            # 确保 worker_module_path 和 worker_class_name 不为 None
            if not worker_module_path or not worker_class_name:
                logger.error(f"❌ 在构建 job 时发现 worker 模块信息为 None!")
                logger.error(f"   entity_id: {entity_id}")
                logger.error(f"   scenario_name: {scenario_name}")
                logger.error(f"   worker_module_path: {worker_module_path}")
                logger.error(f"   worker_class_name: {worker_class_name}")
                logger.error(f"   scenario_cache exists: {scenario_name in self.scenario_cache}")
                if scenario_name in self.scenario_cache:
                    logger.error(f"   Cache keys: {list(self.scenario_cache[scenario_name].keys())}")
                    logger.error(f"   Full cache: {self.scenario_cache[scenario_name]}")
                raise ValueError(f"缺少 worker 模块信息: worker_module_path={worker_module_path}, worker_class_name={worker_class_name}")
            
            job = {
                "id": scenario_model.get_identifier() + "_" + entity_id,
                "payload": {
                    "entity_id": entity_id,
                    "entity_type": entity_type,  # 添加 entity_type
                    "scenario_name": scenario_name,
                    "update_mode": update_mode,
                    "tag_definitions": tag_definitions,  # 使用 tag_definitions 列表
                    "start_date": start_date,
                    "end_date": end_date,
                    "settings": settings,  # 添加完整的 settings
                    "worker_module_path": worker_module_path,  # 用于子进程重新导入
                    "worker_class_name": worker_class_name,  # 用于子进程重新导入
                    "global_extra_cache": global_extra_cache,
                },
            }
            
            # 调试：验证 payload 中是否包含 worker 模块信息
            payload_worker_module_path = job["payload"].get("worker_module_path")
            payload_worker_class_name = job["payload"].get("worker_class_name")
            if not payload_worker_module_path or not payload_worker_class_name:
                logger.error(f"❌ Job payload 中缺少 worker 模块信息!")
                logger.error(f"   Payload keys: {list(job['payload'].keys())}")
                logger.error(f"   worker_module_path in payload: {'worker_module_path' in job['payload']}")
                logger.error(f"   worker_class_name in payload: {'worker_class_name' in job['payload']}")
                logger.error(f"   payload_worker_module_path value: {payload_worker_module_path}")
                logger.error(f"   payload_worker_class_name value: {payload_worker_class_name}")
                logger.error(f"   Original worker_module_path: {worker_module_path}")
                logger.error(f"   Original worker_class_name: {worker_class_name}")
                raise ValueError(f"Job payload 中缺少 worker 模块信息: worker_module_path={payload_worker_module_path}, worker_class_name={payload_worker_class_name}")
                raise ValueError(f"Job payload 中缺少 worker 模块信息")
            jobs.append(job)

        return jobs

    def _execute_jobs(
        self,
        jobs: List[Dict[str, Any]],
        scenario_name: str,
        worker_class: Type[BaseTagWorker],
        *,
        max_workers: Union[str, int] = "auto",
        profile_enabled: bool = False,
        save_batch_size: int = 5000,
    ):
        total_jobs = len(jobs)
        start_time = time.time()
        profile = TagRunProfile(enabled=profile_enabled)

        progress = {"finished": 0, "ok": 0, "fail": 0, "last_pct": -1}
        stager = TagJobStager(
            data_mgr=self.data_mgr,
            contract_cache=self._contract_cache,
        )
        save_buffer = TagReportSaveBuffer(
            self.tag_data_service.save_batch,
            batch_size=save_batch_size,
        )

        def on_stage_job(shell: JobShell) -> StagedJob:
            t0 = time.perf_counter()
            staged = stager.stage(shell)
            profile.record_stage(
                elapsed_sec=time.perf_counter() - t0,
                payload=staged.payload,
            )
            return staged

        def on_report(report: JobReport) -> None:
            t0 = time.perf_counter()
            progress["finished"] += 1
            save_batch_sec = 0.0
            if not report.success:
                progress["fail"] += 1
                logger.error(
                    "Tag job 失败: job_id=%s error=%s",
                    report.job_id,
                    report.error,
                )
            else:
                progress["ok"] += 1
                data = report.data if isinstance(report.data, dict) else {}
                exec_sec = data.get("_profile_execute_sec")
                if isinstance(exec_sec, (int, float)):
                    profile.record_execute(float(exec_sec))
                tag_values = data.get("tag_values") or []
                if tag_values:
                    save_batch_sec = save_buffer.extend(tag_values)

            profile.record_report(
                elapsed_sec=time.perf_counter() - t0,
                save_batch_sec=save_batch_sec,
            )

            finished = progress["finished"]
            pct = int(finished * 100 / total_jobs) if total_jobs else 100
            if finished == total_jobs or pct >= progress["last_pct"] + 5:
                logger.info(
                    "Tag 进度: %s/%s (%s%%) 成功=%s 失败=%s",
                    finished,
                    total_jobs,
                    pct,
                    progress["ok"],
                    progress["fail"],
                )
                progress["last_pct"] = pct

        shells = [JobShell(job_id=job["id"], payload=job["payload"]) for job in jobs]
        executor = create_job_executor(
            ExecutionBackend.PROCESS,
            max_workers=max_workers,
            execute=TagManager._execute_single_job,
            module_name="TagManager",
        )
        logger.info(
            "🚀 开始执行 %s 个 jobs (scenario=%s, workers=%s, config=%r)",
            total_jobs,
            scenario_name,
            executor.max_workers,
            max_workers,
        )
        dispatcher = JobDispatcher(
            on_stage_job=on_stage_job,
            on_report=on_report,
            executor=executor,
        )
        dispatch_result = dispatcher.run(shells)

        save_buffer.flush()

        completed_jobs = dispatch_result.completed
        failed_jobs = dispatch_result.failed
        elapsed_time = time.time() - start_time
        saved_tag_count = save_buffer.saved_row_count

        logger.info(
            f"Tag计算完成: scenario={scenario_name}, "
            f"总jobs={total_jobs}, 成功={completed_jobs}, 失败={failed_jobs}, "
            f"写入tag_values={saved_tag_count}, "
            f"save_batch次数={save_buffer.flush_count}, 耗时={elapsed_time:.2f}秒"
        )
        db_type = ""
        if self.data_mgr and getattr(self.data_mgr, "db", None):
            db_type = str(self.data_mgr.db.config.get("database_type") or "")
        for line in profile.summary_lines(total_jobs=total_jobs, database_type=db_type):
            logger.info(line)

        if self.data_mgr and self.data_mgr.db:
            logger.info("⏳ 等待所有 tag 数据写入完成...")
            self.data_mgr.db.wait_for_writes(timeout=60.0)
            logger.info("✅ 所有 tag 数据写入完成")
            self._maybe_checkpoint_duckdb_after_tag_run()

        return {
            "scenario_name": scenario_name,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "saved_tag_values": saved_tag_count,
            "elapsed_time": elapsed_time,
            "dispatch_result": dispatch_result,
        }

    def _maybe_checkpoint_duckdb_after_tag_run(self) -> None:
        """DuckDB：Tag 写库结束后合并 WAL，避免下次启动回放失败。"""
        db = getattr(self.data_mgr, "db", None) if self.data_mgr else None
        if db is None or str(db.config.get("database_type") or "").lower() != "duckdb":
            return
        if not should_checkpoint_after_tag_run(db.config):
            return
        try:
            logger.info("DuckDB CHECKPOINT（Tag 完成后合并 WAL）…")
            results = db.checkpoint_duckdb()
            failed = [d for d, ok in (results or {}).items() if not ok]
            if failed:
                logger.warning("DuckDB CHECKPOINT 部分失败: %s", failed)
            else:
                logger.info("✅ DuckDB WAL 已合并（domains=%s）", sorted((results or {}).keys()))
        except Exception as exc:
            logger.warning(
                "Tag 完成后 CHECKPOINT 失败（若下次启动报 WAL，可执行: python dev-cli.py -dbc --recover）: %s",
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
            )
            out[dk.value] = list(c.data or [])
        return out

    @staticmethod
    def _execute_single_job(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tag Worker 包装函数（JobExecutor execute）。

        子进程只计算并返回 tag_values；主进程 on_report 负责 save_batch。
        """
        job_id = payload.get("entity_id", "unknown")
        job_payload = payload
        exec_t0 = time.perf_counter()

        try:
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
            result = worker.process_entity()
            execute_sec = time.perf_counter() - exec_t0

            return {
                "success": bool(result.get("success", True)),
                "entity_id": job_payload.get("entity_id"),
                "tag_values": result.get("tag_values") or [],
                "total_tags": result.get("total_tags_created", 0),
                "processed_dates": result.get("processed_dates", 0),
                "total_dates": result.get("total_dates", 0),
                "errors": result.get("errors") or [],
                "_profile_execute_sec": execute_sec,
            }
        except Exception as e:
            logger.exception("Job %s failed: %s", job_id, e)
            return {
                "success": False,
                "entity_id": job_payload.get("entity_id"),
                "tag_values": [],
                "error": str(e),
                "_profile_execute_sec": time.perf_counter() - exec_t0,
            }

