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
from typing import Dict, List, Optional, Type, Any
import logging
from pathlib import Path
from app.tag.core.base_tag_worker import BaseTagWorker
from app.tag.core.components.settings_management.setting_manager import SettingsManager
from app.tag.core.models.scenario_identifier import ScenarioIdentifier
from app.tag.core.components.entity_management.entity_meta_manager import (
    EntityMetaManager,
)
from app.tag.core.components.helper.general_tag_helper import GeneralTagHelper
from app.data_manager import DataManager

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
        #   - self.tag_data_service = data_mgr.get_tag_service()  # TagDataService（DataManager 提供）
        # 注意：不在这里发现 scenarios，延迟到 run() 时

        self.is_verbose = is_verbose
        
        # 初始化字典：scenario 名称 -> scenario 信息字典
        # 每个 scenario 信息包含：
        #   - "worker_class": Type[BaseTagWorker]  # worker 类
        #   - "settings": Dict[str, Any]  # settings 字典
        #   - "instance": Optional[BaseTagWorker]  # worker 实例（缓存，可能为 None）
        self.scenarios: Dict[str, Dict[str, Any]] = {}  # scenario_name -> scenario_setting

        # 初始化 data_mgr（单例模式，内部自动获取）
        self.data_mgr = DataManager(is_verbose=False)
        self.tag_data_service = self.data_mgr.get_tag_service()  # TagDataService（DataManager 提供）
        
    def execute(self):
        """
        执行所有可用的 scenarios（同步执行）
        
        职责：
        1. 使用 GeneralTagHelper.load_scenarios() 加载所有 scenarios
        2. 遍历执行每个 scenario（同步执行，一个完成后才执行下一个）
        
        注意：
        - 执行是同步的：每个 scenario 完全执行完成后，才会执行下一个
        - 每个 scenario 内部使用多进程并行处理 entities
        - 但 scenarios 之间是串行的
        """
        # 1. 加载所有可执行的 scenarios（使用辅助方法）
        all_scenarios = GeneralTagHelper.load_scenarios()
        
        if not all_scenarios:
            logger.info("没有可执行的 scenarios")
            return
        
        logger.info(f"开始执行 {len(all_scenarios)} 个 scenarios（同步执行）")
        
        # 2. 遍历执行每个 scenario（使用标准化的 scenario_info）
        for scenario_info in all_scenarios:
            scenario_name = scenario_info.get("scenario_name")
            if not scenario_name:
                continue
                
            try:
                logger.info(f"开始执行 scenario: {scenario_name}")
                # 直接使用标准化的 scenario_info
                self.execute_single(scenario_name, scenario_info)
                logger.info(f"完成执行 scenario: {scenario_name}")
            except Exception as e:
                logger.error(
                    f"执行 scenario '{scenario_name}' 时出错: {e}",
                    exc_info=True
                )
                # 继续执行下一个 scenario，不中断整个流程
                continue
        
        logger.info("所有 scenarios 执行完成")

    def execute_single(
        self, 
        scenario_name: str, 
        scenario_info: Dict[str, Any] = None
    ):
        """
        执行单个 scenario
        
        职责：
        1. 获取标准化的 scenario_info（使用 GeneralTagHelper 辅助方法）
        2. 确保元信息存在（scenario 和 tag definitions）
        3. 构建 jobs
        4. 执行多进程计算
        
        支持两种场景：
        1. 没有 scenario_info：从文件系统加载（使用 GeneralTagHelper.load_scenario_by_name）
        2. 有 scenario_info：使用提供的标准化 scenario_info（包含 scenario_name, settings, worker_class）
        
        Args:
            scenario_name: Scenario 名称（必需）
            scenario_info: 标准化的 scenario_info 字典（可选），包含：
                - "scenario_name": str
                - "settings": Dict[str, Any]
                - "worker_class": type[BaseTagWorker]
                如果不提供则从文件系统加载
        """
        # 1. 获取标准化的 scenario_info（使用辅助方法）
        if not scenario_info:
            # 场景1：从文件系统加载（用户单个执行某个 tag 的 job）
            scenario_info = GeneralTagHelper.load_scenario_by_name(scenario_name)
            if not scenario_info:
                raise ValueError(f"can not find scenario by name: {scenario_name}")
        else:
            # 场景2：用户提供了 scenario_info，验证其结构
            # 确保 scenario_name 一致
            info_scenario_name = scenario_info.get("scenario_name")
            if info_scenario_name and info_scenario_name != scenario_name:
                logger.warning(
                    f"scenario_info 中的 scenario_name ({info_scenario_name}) "
                    f"与传入的 scenario_name ({scenario_name}) 不匹配，使用 scenario_info 中的 name"
                )
                scenario_name = info_scenario_name
        
        # 2. 从标准化的 scenario_info 中提取信息
        settings = scenario_info["settings"]
        worker_class = scenario_info["worker_class"]
        
        # 3. 验证 settings 有效性（包装成 scenario_setting 格式）
        scenario_setting = {
            "scenario_name": scenario_name,
            "settings": settings,
            "worker_class": worker_class,
        }
        if not SettingsManager.is_valid_scenario_setting(scenario_setting):
            raise ValueError(f"scenario {scenario_name} settings is not valid")
        
        # 3. 确保元信息存在（scenario 和 tag definitions），并获取日期范围
        scenario, tag_defs, version_action, start_date, end_date = EntityMetaManager.ensure_metadata(
            self.tag_data_service, scenario_setting
        )

        # 4. 构建 jobs
        jobs = self._build_jobs(scenario_setting, tag_defs, start_date, end_date)
        
        if not jobs:
            logger.warning(f"No jobs to execute for scenario: {scenario_name}")
            return

        # 5. 决定进程数（使用通用 helper）
        max_workers = GeneralTagHelper.decide_worker_amount(jobs)

        logger.info(
            f"开始执行 scenario: {scenario_name}, "
            f"jobs={len(jobs)}, max_workers={max_workers}"
        )

        # 6. 执行多进程计算
        from utils.worker.multi_process.process_worker import ProcessWorker, ExecutionMode
        
        worker_pool = ProcessWorker(
            max_workers=max_workers,
            execution_mode=ExecutionMode.QUEUE,  # 队列模式，持续填充
            job_executor=TagManager._tag_worker_wrapper,  # 静态方法
            is_verbose=self.is_verbose
        )
        
        # 执行 jobs
        stats = worker_pool.run_jobs(jobs)
        
        # 7. 收集结果和统计信息
        successful_results = worker_pool.get_successful_results()
        failed_results = worker_pool.get_failed_results()
        
        logger.info(
            f"Tag计算完成: scenario={scenario_name}, "
            f"成功={len(successful_results)}, 失败={len(failed_results)}"
        )
        
        # 打印统计信息
        worker_pool.print_stats()

    def _build_jobs(
        self, 
        scenario_setting: Dict[str, Any],
        tag_defs: List[Dict[str, Any]],
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        构建 jobs（每个 entity 一个 job）
        
        职责：
        1. 获取实体列表（股票列表）
        2. 为每个 entity 创建一个 job
        
        Args:
            scenario_setting: Scenario settings 字典，包含：
                - "scenario_name": str
                - "worker_class": Type[BaseTagWorker]
                - "settings": Dict[str, Any]
                - "worker_file_path": str
                - "settings_file_path": str
            tag_defs: Tag Definition 列表
            start_date: 起始日期
            end_date: 结束日期
        
        Returns:
            List[Dict[str, Any]]: Job列表
        """
        jobs = []
        
        # 1. 获取实体列表
        entities = self._get_entity_list()
        
        if not entities:
            logger.warning(f"没有实体需要计算: scenario={scenario_setting['scenario_name']}")
            return jobs
        
        # 5. 为每个 entity 创建 job
        # 注意：直接传递完整的 settings 字典，避免在子进程中重复加载
        # 这样如果 settings 结构变化，只需要改 BaseTagWorker 一处即可
        for entity_id in entities:
            job = {
                "id": f"{entity_id}_{scenario_setting['scenario_name']}",
                "payload": {
                    # 实体信息
                    "entity_id": entity_id,
                    "entity_type": "stock",
                    
                    # Scenario 信息
                    "scenario_name": scenario_setting["scenario_name"],
                    "scenario_version": scenario_setting["settings"]["scenario"]["version"],
                    
                    # Tag 信息（必需，因为需要 tag_definition_id）
                    "tag_definitions": tag_defs,
                    
                    # 日期范围（必需）
                    "start_date": start_date,
                    "end_date": end_date,
                    
                    # Worker 实例化所需（子进程中需要）
                    "worker_class": scenario_setting["worker_class"],
                    "settings": scenario_setting["settings"],  # 直接传完整的 settings 字典
                }
            }
            jobs.append(job)
        
        return jobs

    def _get_entity_list(self) -> List[str]:
        """
        获取实体列表（股票列表）
        
        职责：
        1. 从 DataManager 获取股票列表
        2. 返回实体ID列表
        
        Returns:
            List[str]: 实体ID列表
        """
        if not self.data_mgr:
            raise ValueError("DataManager 未初始化，无法获取实体列表")
        
        # 使用 DataManager 的 get_stock_list 方法
        if hasattr(self.data_mgr, "get_stock_list"):
            stock_list = self.data_mgr.get_stock_list()
            return [stock.get('id') for stock in stock_list if stock.get('id')]
        
        # 备用方案：使用 StockModel
        try:
            stock_model = self.data_mgr.get_model("stock")
            if stock_model:
                stocks = stock_model.get_all()
                return [stock.get('id') for stock in stocks if stock.get('id')]
        except Exception as e:
            logger.warning(f"获取股票列表失败: {e}")
        
        return []
  
    def refresh_scenarios(self):
        """
        刷新 scenarios（重新发现和加载）
        
        职责：
        1. 重新发现所有 scenarios（使用 GeneralTagHelper.load_scenarios）
        2. 更新内部状态（如果需要）
        
        用于动态加载新添加的 scenario
        """
        # 重新加载所有 scenarios（使用辅助方法）
        all_scenarios = GeneralTagHelper.load_scenarios()
        logger.info(f"刷新完成，共 {len(all_scenarios)} 个可执行的 scenarios")

    # # ========================================================================
    # ========================================================================
    # 多进程 Worker Wrapper（静态方法，用于 ProcessWorker）
    # ========================================================================
    
    @staticmethod
    def _tag_worker_wrapper(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tag Worker 包装函数（用于 ProcessWorker 的 job_executor）
        
        在子进程中：
        1. 初始化 DataManager 和 TagDataService
        2. 实例化 TagWorker（从 settings 自动加载所有配置）
        3. 调用 worker.process_entity() 处理单个 entity
        
        Args:
            payload: Job payload 字典，包含：
                - entity_id: 实体ID
                - entity_type: 实体类型
                - scenario_name: Scenario 名称
                - scenario_version: Scenario 版本
                - tag_definitions: Tag Definition 列表
                - start_date: 起始日期
                - end_date: 结束日期
                - worker_class: Worker 类（用于实例化）
                - settings: Settings 字典（完整的 settings 配置）
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        # 1. 初始化 DataManager 和 TagDataService（子进程中）
        from app.data_manager import DataManager
        data_mgr = DataManager(is_verbose=False)
        tag_data_service = data_mgr.get_tag_service()
        
        # 2. 获取 worker 类和 settings 字典
        worker_class = payload['worker_class']
        settings = payload['settings']  # 直接使用传入的完整 settings 字典
        
        # 3. 创建 worker 实例（子进程中）
        # 注意：直接传入 settings 字典，避免重复加载文件
        # 这样如果 settings 结构变化，只需要改 BaseTagWorker 一处即可
        worker = worker_class(
            settings=settings,  # 直接传入 settings 字典
            data_mgr=data_mgr,
            tag_data_service=tag_data_service
        )
        
        # 4. 调用 process_entity 方法
        return worker.process_entity(payload)
