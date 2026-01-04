"""
Tag Manager - 统一管理所有业务场景（Scenario）

职责：
1. 发现和加载所有 scenario workers
2. 检查 settings 文件存在性
3. 统一验证所有 settings（schema 校验）
4. 提供统一的接口访问 workers
5. 负责多进程调度（job构建、进程数决定、ProcessWorker调用）
6. 支持手动注册 scenario（未来实现）

注意：
- 元信息的创建在 Worker 中处理（支持手动注册）
- Settings 验证在 TagManager 层统一处理
- DataManager 是单例模式，内部自动获取
- 多进程调度由 TagManager 负责
"""
import time
from typing import Dict, List, Optional, Type, Any, Tuple
import logging
from pathlib import Path
from app.core.modules.tag.core.enums import TagUpdateMode
from app.core.modules.tag.core.base_tag_worker import BaseTagWorker
from app.core.modules.tag.core.components.helper.tag_helper import TagHelper
from app.core.modules.tag.core.components.helper.job_helper import JobHelper
from app.core.modules.data_manager import DataManager
from app.core.modules.tag.core.config import DEFAULT_SCENARIOS_ROOT
from app.core.modules.tag.core.enums import FileName
from app.core.modules.tag.core.models.scenario_model import ScenarioModel
from app.core.infra.worker.multi_process.process_worker import ExecutionMode, ProcessWorker

logger = logging.getLogger(__name__)

class TagManager:
    """
    Tag Manager - 统一管理所有业务场景（Scenario）
    
    职责：
    1. 发现和加载所有 scenario workers
    2. 检查 settings 文件存在性
    3. 统一验证所有 settings（schema 校验）
    4. 提供统一的接口访问 workers
    5. 负责多进程调度（job构建、进程数决定、ProcessWorker调用）
    6. 支持手动注册 scenario（未来实现）
    
    注意：
    - 元信息的创建在 Worker 中处理（支持手动注册）
    - Settings 验证在 TagManager 层统一处理
    - 多进程调度由 TagManager 负责
    """
    
    def __init__(self, is_verbose = False):
        """
        初始化 TagManager
        
        DataManager 是单例模式，内部自动获取，不需要外部注入
        """
        # 从配置读取 scenarios 根目录（DEFAULT_SCENARIOS_ROOT）
        # 初始化字典：scenario 名称 -> scenario 信息字典
        # 每个 scenario 信息包含：
        #   - "worker_class": Type[BaseTagWorker]  # worker 类
        #   - "settings": Dict[str, Any]  # settings 字典
        #   - "instance": Optional[BaseTagWorker]  # worker 实例（缓存，可能为 None）
        # 初始化 data_mgr（单例模式，内部自动获取）
        # 初始化 DataManager 的 tag 服务：
        # 注意：不在这里发现 scenarios，延迟到 run() 时

        # 是否输出详细日志
        self.is_verbose = is_verbose
        
        # 初始化 data_mgr（单例模式，内部自动获取）
        self.data_mgr = DataManager(is_verbose=False)
        self.tag_data_service = self.data_mgr.tag

        # 可用场景缓存
        self.scenario_cache = {}

        # 不同场景间的实体列表缓存
        self.entity_list_cache = {}

        # 场景发现并缓存
        self._discover_scenarios_from_folder()

    def refresh_scenario(self):
        self._clear_cache()
        self.scenario_cache = self._discover_scenarios_from_folder()

    def execute(self, scenario_name: str = None, settings: Dict[str, Any] = None):
        if settings:
            self._execute_single_from_tmp_settings(settings)
        elif scenario_name:  
            self._execute_single(scenario_name)
        else:
            self._execute_all()
        self._clear_cache()

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

    # discover and cache scenario settings from folder
    def _discover_scenarios_from_folder(self):
        scenario_cache = {}
        root_folder = Path(DEFAULT_SCENARIOS_ROOT)

        for scenario_folder in root_folder.iterdir():
            if not scenario_folder.is_dir():
                continue

            cache_item = self._build_scenario_cache(scenario_folder)
            if not cache_item:
                continue      

            scenario_cache[cache_item["name"]] = cache_item
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

        return {
            "name": scenario_name,
            "scenario_folder_path": scenario_folder.name,
            "settings": settings_dict,
            "settings_file_path": settings_path,
            "worker_class": worker_class,
            "worker_file_path": worker_class_path,
        }

    def _load_scenario_from_cache_by_name(self, name: str):
        if name in self.scenario_cache:
            return self.scenario_cache[name]
        else:
            return None

    def _get_entity_list(self, scenario_model: ScenarioModel) -> List[str]:
        """
        获取实体列表
        
        Args:
            scenario_model: ScenarioModel 实例
            
        Returns:
            List[str]: 实体ID列表
        """
        from app.core.global_enums.enums import EntityType
        
        target_entity_str = scenario_model.get_target_entity()
        
        # 使用缓存
        if target_entity_str in self.entity_list_cache:
            return self.entity_list_cache[target_entity_str]
        
        # 将字符串转换为 EntityType 枚举
        try:
            entity_type = EntityType(target_entity_str)
        except ValueError:
            logger.warning(f"不支持的实体类型: {target_entity_str}")
            return []
        
        # 使用 DataManager 的 load_entity_list 方法
        entity_list = self.data_mgr.load_entity_list(
            entity_type=entity_type,
            filtered=True  # 默认使用过滤规则
        )
        
        # 缓存结果
        self.entity_list_cache[target_entity_str] = entity_list
        return entity_list

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
        tag_data_service = self.data_mgr.tag
        if not tag_data_service:
            logger.error(f"无法获取 tag_data_service，跳过执行")
            return
        scenario_model.ensure_metadata(tag_data_service)

        # 获取实体列表
        entity_list = self._get_entity_list(scenario_model)
        if not entity_list:
            logger.info(f"无法获取实体列表，跳过执行")
            return

        # 获取 worker_class（从 cache 中获取，如果不在 cache 中则尝试从 settings 加载）
        scenario_name = scenario_model.get_name()
        worker_class = self._get_worker_class(scenario_name, scenario_model)
        if not worker_class:
            logger.error(f"无法获取 worker_class，跳过执行: scenario={scenario_name}")
            return

        # 获取更新模式
        settings = scenario_model.get_settings()

        jobs = self._build_jobs(entity_list, settings, scenario_model, worker_class)

        if not jobs:
            logger.warning(f"没有新的计算任务，跳过执行: scenario={scenario_name}")
            return

        # 执行 jobs
        # 从 settings 中获取 max_workers 配置
        performance = settings.get("performance", {})
        max_workers = performance.get("max_workers", "auto")
        worker_amount = JobHelper.decide_worker_amount(len(jobs), max_workers=max_workers)
        self._execute_jobs(jobs, scenario_name, worker_class, worker_amount)

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
        
        # 获取默认日期
        default_start_date = settings.get("start_date")
        default_end_date = settings.get("end_date")
        
        # 获取实体类型（从 scenario_model 获取）
        entity_type = scenario_model.get_target_entity()
        
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
            tag_data_service = self.data_mgr.tag
            if tag_data_service:
                entity_last_update_info = tag_data_service.get_tag_value_last_update_info(scenario_name)
        
        jobs = []

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
            scenario_cache = self.scenario_cache.get(scenario_name, {})
            worker_module_path = scenario_cache.get("worker_module_path")
            worker_class_name = scenario_cache.get("worker_class_name")
            
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
                },
            }
            jobs.append(job)

        return jobs

    def _execute_jobs(self, jobs: List[Dict[str, Any]], scenario_name: str, worker_class: Type[BaseTagWorker], worker_amount: int):
        
        worker_pool = ProcessWorker(
            max_workers=worker_amount,
            execution_mode=ExecutionMode.QUEUE,  # 队列模式，持续填充
            job_executor=TagManager._execute_single_job,  # 静态方法
            is_verbose=False  # 关闭 ProcessWorker 的详细日志，由 TagManager 统一控制
        )

        # 执行 jobs 并实时反馈进度
        total_jobs = len(jobs)
        start_time = time.time()

        logger.info(f"开始执行 {total_jobs} 个 jobs...")
        
        # 执行 jobs（ProcessWorker 内部会处理多进程和进度）
        # 注意：进度反馈在 ProcessWorker 内部已经实现（每10个job输出一次）
        # 如果需要更详细的进度，可以在 ProcessWorker 中添加回调机制
        stats = worker_pool.run_jobs(jobs)
        
        # 在等待期间，定期输出进度（如果 ProcessWorker 支持）
        # 由于 ProcessWorker 内部已经处理了进度，我们主要在这里做最终统计
        
        # 4. 收集结果和统计信息
        successful_results = worker_pool.get_successful_results()
        failed_results = worker_pool.get_failed_results()
        
        # 计算最终统计
        completed_jobs = len(successful_results)
        failed_jobs = len(failed_results)
        elapsed_time = time.time() - start_time
        
        logger.info(
            f"Tag计算完成: scenario={scenario_name}, "
            f"总jobs={total_jobs}, 成功={completed_jobs}, 失败={failed_jobs}, "
            f"耗时={elapsed_time:.2f}秒"
        )
        
        # 打印详细统计信息
        if self.is_verbose:
            worker_pool.print_stats()
        
        # 返回统计信息（可选，用于上层调用）
        return {
            'scenario_name': scenario_name,
            'total_jobs': total_jobs,
            'completed_jobs': completed_jobs,
            'failed_jobs': failed_jobs,
            'elapsed_time': elapsed_time,
            'stats': stats
        }

    @staticmethod
    def _execute_single_job(job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tag Worker 包装函数（用于 ProcessWorker 的 job_executor）
        
        在子进程中：
        1. 从 job payload 中提取信息
        2. 实例化 TagWorker（传入完整的 job_payload）
        3. 调用 worker.run() 执行计算
        """
        from app.core.infra.worker.multi_process.process_worker import JobResult, JobStatus
        from datetime import datetime
        
        job_id = job.get('id', 'unknown')
        payload = job.get('payload', {})
        
        try:
            # 1. 在子进程中重新导入 worker_class（避免 pickle 问题）
            import importlib
            worker_module_path = payload.get('worker_module_path')
            worker_class_name = payload.get('worker_class_name')
            
            if not worker_module_path or not worker_class_name:
                raise ValueError(f"缺少 worker 模块信息: worker_module_path={worker_module_path}, worker_class_name={worker_class_name}")
            
            # 动态导入模块和类
            worker_module = importlib.import_module(worker_module_path)
            worker_class = getattr(worker_module, worker_class_name)
            
            job_payload = payload  # 完整的 payload 传给 worker
            
            # 2. 创建 worker 实例（子进程中）
            # 注意：
            # - 直接传入 job_payload，包含所有必要信息
            # - DataManager 是单例模式，在 BaseTagWorker.__init__ 中会自动初始化
            worker = worker_class(job_payload=job_payload)
            
            # 3. 调用 process_entity() 方法执行计算
            result = worker.process_entity()
            
            # 4. 返回成功结果
            return JobResult(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                result={
                    'entity_id': payload.get('entity_id'),
                    'success': result.get('success', True),
                    'total_tags': result.get('total_tags_created', 0),
                    'processed_dates': result.get('processed_dates', 0),
                    'total_dates': result.get('total_dates', 0)
                },
                start_time=datetime.now(),
                end_time=datetime.now()
            )
            
        except Exception as e:
            # 返回失败结果
            import traceback
            logger.exception(f"Job {job_id} failed: {e}")
            return JobResult(
                job_id=job_id,
                status=JobStatus.FAILED,
                error=str(e),
                result={
                    'entity_id': payload.get('entity_id'),
                    'success': False,
                    'error': str(e)
                },
                start_time=datetime.now(),
                end_time=datetime.now()
            )

