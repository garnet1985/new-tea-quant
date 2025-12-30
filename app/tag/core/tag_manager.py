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
import importlib.util
import logging
from pathlib import Path
from app.tag.core.base_tag_worker import BaseTagWorker
from app.tag.core.components.settings_management.setting_manager import (
    settings_manager,
)
from app.tag.core.config import DEFAULT_SCENARIOS_ROOT
from app.tag.core.models.scenario_identifier import ScenarioIdentifier
from app.tag.core.components.entity_management.entity_meta_manager import (
    EntityMetaManager,
)
from app.data_manager import DataManager
from utils.file.file_util import FileUtil

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
        
        # 从配置读取 scenarios 根目录
        self.scenarios_root = Path(DEFAULT_SCENARIOS_ROOT)
        
        # 初始化字典：scenario 名称 -> scenario 信息字典
        # 每个 scenario 信息包含：
        #   - "worker_class": Type[BaseTagWorker]  # worker 类
        #   - "settings": Dict[str, Any]  # settings 字典
        #   - "instance": Optional[BaseTagWorker]  # worker 实例（缓存，可能为 None）
        self.scenarios: Dict[str, Dict[str, Any]] = {}  # scenario_name -> scenario_setting
        
        # 初始化 data_mgr（单例模式，内部自动获取）
        self.data_mgr = DataManager(is_verbose=False)
        self.tag_data_service = self.data_mgr.get_tag_service()  # TagDataService（DataManager 提供）

        # 初始化 EntityMetaManager
        self.entity_meta_manager = EntityMetaManager(self.tag_data_service)
        

    def execute(self):
        """
        执行所有可用的 scenarios（同步执行）
        
        职责：
        1. 加载所有 scenarios
        2. 遍历执行每个 scenario（同步执行，一个完成后才执行下一个）
        
        注意：
        - 执行是同步的：每个 scenario 完全执行完成后，才会执行下一个
        - 每个 scenario 内部使用多进程并行处理 entities
        - 但 scenarios 之间是串行的
        """
        all_scenario_settings = self._load_all_scenarios()
        
        logger.info(f"开始执行 {len(all_scenario_settings)} 个 scenarios（同步执行）")
        
        for scenario_setting in all_scenario_settings:
            scenario_name = scenario_setting.get("scenario_name")
            if scenario_name:
                logger.info(f"开始执行 scenario: {scenario_name}")
                try:
                    self.execute_single(scenario_name)
                    logger.info(f"完成执行 scenario: {scenario_name}")
                except Exception as e:
                    logger.error(
                        f"执行 scenario '{scenario_name}' 时出错: {e}",
                        exc_info=True
                    )
                    # 继续执行下一个 scenario，不中断整个流程
                    continue
        
        logger.info("所有 scenarios 执行完成")


    def execute_single(self, scenario_name: str, scenario_setting: Dict[str, Any] = None):
        """
        执行单个 scenario
        
        职责：
        1. 获取或验证 scenario_setting
        2. 验证 settings 有效性
        3. 检查 is_enabled
        4. 构建 jobs
        5. 执行多进程计算
        
        支持两种场景：
        1. 已存在的 scenario（只传 scenario_name）：从文件系统加载
        2. 新的 scenario（传 scenario_name 和 scenario_setting）：使用传入的 settings
        
        Args:
            scenario_name: Scenario 名称（必需）
            scenario_setting: Scenario settings 字典（可选，如果不提供则从文件系统加载）
        """
        # 1. 验证 scenario 是否可执行
        if not self._is_executable_scenario(scenario_name, scenario_setting):
            return
        
        # 2. 存储到内部字典（用于后续访问）
        self.scenarios[scenario_name] = scenario_setting

        # 3. 确保元信息存在（scenario 和 tag definitions），并获取日期范围
        scenario, tag_defs, version_action, start_date, end_date = self.entity_meta_manager.ensure_metadata(scenario_setting)

        # 4. 构建 jobs
        jobs = self._build_jobs(scenario_setting, tag_defs, start_date, end_date)
        
        if not jobs:
            logger.warning(f"No jobs to execute for scenario: {scenario_name}")
            return

        # 6. 决定进程数
        max_workers = self._decide_worker_amount(jobs)

        # 7. 执行多进程计算
        from utils.worker.multi_process.process_worker import ProcessWorker, ExecutionMode
        
        worker_pool = ProcessWorker(
            max_workers=max_workers,
            execution_mode=ExecutionMode.QUEUE,  # 队列模式，持续填充
            job_executor=TagManager._tag_worker_wrapper,  # 静态方法
            is_verbose=self.is_verbose
        )
        
        # 执行 jobs
        stats = worker_pool.run_jobs(jobs)
        
        # 8. 收集结果和统计信息
        successful_results = worker_pool.get_successful_results()
        failed_results = worker_pool.get_failed_results()
        
        logger.info(
            f"Tag计算完成: scenario={scenario_name}, "
            f"成功={len(successful_results)}, 失败={len(failed_results)}"
        )
        
        # 打印统计信息
        worker_pool.print_stats()

    def _is_executable_scenario(self, scenario_name: str, scenario_setting: Dict[str, Any] = None) -> bool:
        """
        验证 scenario
        
        职责：
        1. 验证 scenario 是否有效
        2. 返回验证结果
        """
        if scenario_name is None:
            raise ValueError("scenario_name is required")

        # 1. 获取 scenario_setting（如果未提供，从文件系统加载）
        if scenario_setting is None:
            scenario_setting = self._get_scenario_setting(scenario_name)

        if not scenario_setting:
            raise ValueError(f"can not find scenario by name {scenario_name}.")

        # 2. 验证 settings 有效性
        if not settings_manager.is_valid_scenario_setting(scenario_setting):
            logger.warning(f"{scenario_name} settings is not valid, skip execution")
            return False

        # 3. 检查 is_enabled
        if not scenario_setting.get("is_enabled", False):
            logger.info(f"{scenario_name} is not enabled, skip execution")
            return False

        return True

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
        # 注意：只传必要参数，其他参数（base_term, required_terms, required_data, core, tags_config 等）
        # 可以从 settings 中获取，在子进程中 worker 实例化时会自动加载
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
                    "settings_path": scenario_setting["settings_file_path"],
                    
                    # 注意：base_term, required_terms, required_data, core, tags_config 等
                    # 不需要传，worker 实例化时会从 settings 中自动加载
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


    def _decide_worker_amount(self, jobs: List[Dict[str, Any]]) -> int:
        """
        决定 worker 数量（进程数）
        
        职责：
        1. 根据 job 数量决定进程数（最多10个）
        2. 考虑 scenario 配置的 max_workers
        
        策略：
        1. 如果配置了 max_workers，使用配置值（但不超过10）
        2. 如果 job 数量 <= 1，使用1个进程
        3. 如果 job 数量 <= 5，使用2个进程
        4. 如果 job 数量 <= 10，使用3个进程
        5. 如果 job 数量 <= 20，使用5个进程
        6. 如果 job 数量 <= 50，使用8个进程
        7. 否则使用10个进程（最大）
        
        Args:
            jobs: Job列表
        
        Returns:
            int: 进程数
        """
        job_count = len(jobs)
        
        # 从当前 scenario 的 settings 中获取 max_workers 配置
        # 注意：这里需要从 scenario_setting 中获取，但 jobs 中没有直接包含
        # 暂时使用默认策略，后续可以从 scenario_setting 中获取
        
        # 根据 job 数量决定
        if job_count <= 1:
            return 1
        elif job_count <= 5:
            return 2
        elif job_count <= 10:
            return 3
        elif job_count <= 20:
            return 5
        elif job_count <= 50:
            return 8
        else:
            return 10  # 最大10个进程

    def _load_all_scenarios(self) -> List[Dict[str, Any]]:
        """
        加载所有 scenarios（发现和过滤）
        
        职责：
        1. 发现所有 scenarios（扫描目录并加载文件）
        2. 过滤出可执行的 scenarios（验证、检查 is_enabled）
        3. 返回可执行的 scenario 列表
        
        Returns:
            List[Dict[str, Any]]: 可执行的 scenario 列表
        """
        # 1. 发现所有 scenarios
        all_scenarios = self._discover_scenarios()
        
        # 2. 过滤出可执行的 scenarios
        executable_scenarios = self._filter_executable_scenarios(all_scenarios)
        
        return executable_scenarios
    
    def _get_scenario_setting(self, scenario_name: str) -> Optional[Dict[str, Any]]:
        """
        根据 scenario_name 获取 scenario_setting
        
        职责：
        1. 从内部字典（self.scenarios）中查找
        2. 如果不存在，从文件系统加载
        
        Args:
            scenario_name: Scenario 名称
        
        Returns:
            Optional[Dict[str, Any]]: Scenario setting 字典，如果不存在返回 None
        """
        # 1. 先从内部字典查找（可能已经加载过）
        if scenario_name in self.scenarios:
            return self.scenarios[scenario_name]
        
        # 2. 从文件系统加载
        all_scenarios = self._discover_scenarios()
        
        for scenario_info in all_scenarios:
            if scenario_info.get("scenario_name") == scenario_name:
                # 过滤验证
                executable_scenarios = self._filter_executable_scenarios([scenario_info])
                if executable_scenarios:
                    return executable_scenarios[0]
        
        return None
    
    def _discover_scenarios(self) -> List[Dict[str, Any]]:
        """
        发现所有 scenarios（扫描目录并加载文件）
        
        职责：
        1. 扫描 scenarios 目录，发现所有 scenario 子目录
        2. 对每个 scenario：
           a. 检查必需文件（tag_worker.py, settings.py）是否存在
           b. 加载 settings 文件（不验证）
           c. 加载 worker 类
        3. 返回所有发现的 scenario 信息列表（包括无效的）
        
        Returns:
            List[Dict[str, Any]]: 所有发现的 scenario 信息列表
        """
        all_scenarios = []
        
        # 1. 检查 scenarios 目录是否存在
        if not FileUtil.dir_exists(str(self.scenarios_root)):
            logger.warning(f"Scenarios 目录不存在: {self.scenarios_root}")
            return all_scenarios
        
        # 2. 遍历 scenarios 目录下的所有子目录
        for scenario_dir in self.scenarios_root.iterdir():
            if not scenario_dir.is_dir():
                continue
            
            scenario_name = scenario_dir.name
            scenario_info = {
                "scenario_name": scenario_name,
                "worker_class": None,
                "settings": None,
                "worker_file_path": None,
                "settings_file_path": None,
                "error": None,
            }
            
            # 2.1 检查 tag_worker.py 是否存在（递归查找）
            worker_file_path = FileUtil.find_file_in_folder(
                "tag_worker.py",
                str(scenario_dir),
                is_recursively=True
            )
            if not worker_file_path:
                scenario_info["error"] = f"缺少 tag_worker.py 文件"
                all_scenarios.append(scenario_info)
                if self.is_verbose:
                    logger.warning(
                        f"Scenario '{scenario_name}' 缺少 tag_worker.py 文件"
                    )
                continue
            
            scenario_info["worker_file_path"] = worker_file_path
            
            # 2.2 检查 settings.py 是否存在（递归查找）
            settings_file_path = FileUtil.find_file_in_folder(
                "settings.py",
                str(scenario_dir),
                is_recursively=True
            )
            if not settings_file_path:
                scenario_info["error"] = f"缺少 settings.py 文件"
                all_scenarios.append(scenario_info)
                if self.is_verbose:
                    logger.warning(
                        f"Scenario '{scenario_name}' 缺少 settings.py 文件"
                    )
                continue
            
            scenario_info["settings_file_path"] = settings_file_path
            
            # 2.3 加载 settings（不验证，只加载）
            try:
                settings = self._load_settings(Path(settings_file_path))
                scenario_info["settings"] = settings
            except Exception as e:
                scenario_info["error"] = f"加载 settings 失败: {e}"
                all_scenarios.append(scenario_info)
                logger.warning(
                    f"加载 scenario '{scenario_name}' 的 settings 失败: {e}",
                    exc_info=True
                )
                continue
            
            # 2.4 加载 worker 类
            try:
                worker_class = self._load_worker(Path(worker_file_path))
                scenario_info["worker_class"] = worker_class
            except Exception as e:
                scenario_info["error"] = f"加载 worker 失败: {e}"
                all_scenarios.append(scenario_info)
                logger.warning(
                    f"加载 scenario '{scenario_name}' 的 worker 失败: {e}",
                    exc_info=True
                )
                continue
            
            # 2.5 添加到列表（加载成功）
            all_scenarios.append(scenario_info)
            
            if self.is_verbose:
                logger.debug(f"发现 scenario: {scenario_name}")
        
        logger.info(f"共发现 {len(all_scenarios)} 个 scenarios")
        return all_scenarios
    
    def _filter_executable_scenarios(self, all_scenarios: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤出可执行的 scenarios
        
        职责：
        1. 对每个 scenario 进行验证：
           a. 检查是否有错误（加载失败）
           b. 检查 is_enabled 字段
           c. 验证 settings 结构
           d. 验证枚举值
        2. 返回所有通过验证的 scenario 信息列表
        
        Args:
            all_scenarios: 所有发现的 scenario 信息列表（来自 _discover_scenarios）
        
        Returns:
            List[Dict[str, Any]]: 可执行的 scenario 信息列表
        """
        executable_scenarios = []
        
        for scenario_info in all_scenarios:
            scenario_name = scenario_info["scenario_name"]
            
            # 1. 检查是否有错误（加载失败）
            if scenario_info.get("error"):
                # 已有错误，跳过
                continue
            
            # 2. 检查必需字段是否存在
            if not scenario_info.get("settings"):
                logger.warning(
                    f"Scenario '{scenario_name}' 缺少 settings，跳过"
                )
                continue
            
            if not scenario_info.get("worker_class"):
                logger.warning(
                    f"Scenario '{scenario_name}' 缺少 worker_class，跳过"
                )
                continue
            
            settings = scenario_info["settings"]
            
            # 3. 检查 is_enabled 字段
            if "is_enabled" not in settings:
                logger.warning(
                    f"Scenario '{scenario_name}' 缺少 'is_enabled' 字段，跳过"
                )
                continue
            
            if not settings.get("is_enabled", False):
                if self.is_verbose:
                    logger.info(f"Scenario '{scenario_name}' 被禁用 (is_enabled=False)，跳过")
                continue
            
            # 4. 验证 settings（结构和枚举）
            try:
                settings_manager.validate_settings(settings)
            except ValueError as e:
                logger.warning(
                    f"Scenario '{scenario_name}' 的 settings 验证失败: {e}，跳过"
                )
                continue
            
            # 6. 添加到可执行列表（移除 error 字段，只保留有效信息）
            executable_scenario = {
                "scenario_name": scenario_info["scenario_name"],
                "worker_class": scenario_info["worker_class"],
                "settings": scenario_info["settings"],
                "worker_file_path": scenario_info["worker_file_path"],
                "settings_file_path": scenario_info["settings_file_path"],
            }
            executable_scenarios.append(executable_scenario)
            
            if self.is_verbose:
                logger.info(f"可执行 scenario: {scenario_name}")
        
        return executable_scenarios
    
    def _load_settings(self, settings_file: Path) -> Dict[str, Any]:
        """
        加载 settings 文件
        
        职责：
        1. 读取 settings.py 文件
        2. 应用默认值
        3. 返回处理后的 settings 字典
        
        Args:
            settings_file: settings.py 文件路径
            
        Returns:
            Dict[str, Any]: Settings 字典
            
        Raises:
            ValueError: settings 文件格式错误
        """
        # 使用 SettingsManager 读取并应用默认值
        return settings_manager.load_settings_from_file(str(settings_file))
    
    def _load_worker(self, worker_file: Path) -> Type[BaseTagWorker]:
        """
        加载 worker 类
        
        职责：
        1. 动态导入 worker 模块
        2. 查找继承自 BaseTagWorker 的类
        3. 返回 worker 类
        
        Args:
            worker_file: tag_worker.py 文件路径
            
        Returns:
            Type[BaseTagWorker]: Worker 类
            
        Raises:
            ValueError: 如果无法加载或找不到 worker 类
        """
        # 动态导入模块
        spec = importlib.util.spec_from_file_location("tag_worker", worker_file)
        if spec is None or spec.loader is None:
            raise ValueError(f"无法加载 worker 文件: {worker_file}")
        
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except SyntaxError as e:
            raise ValueError(f"Worker 文件语法错误: {worker_file}\n{str(e)}")
        except Exception as e:
            raise ValueError(f"导入 worker 文件失败: {worker_file}\n{str(e)}")
        
        # 查找继承自 BaseTagWorker 的类
        worker_class = None
        for name, obj in module.__dict__.items():
            if (isinstance(obj, type) and 
                issubclass(obj, BaseTagWorker) and 
                obj != BaseTagWorker):
                worker_class = obj
                break
        
        if worker_class is None:
            raise ValueError(
                f"Worker 文件中没有找到继承自 BaseTagWorker 的类: {worker_file}"
            )
        
        return worker_class


    def refresh_scenarios(self):
        """
        刷新 scenarios（重新发现和加载）
        
        职责：
        1. 重新发现所有 scenarios
        2. 重新过滤可执行的 scenarios
        3. 更新内部状态（如果需要）
        
        用于动态加载新添加的 scenario
        """
        # 重新加载可执行的 scenarios
        self._load_executable_scenarios()

    
    # def run(self, scenario_name: str = None):
    #     """
    #     执行 scenarios 的计算（入口函数）
        
    #     Tag 系统是预计算系统，数据应该从数据库（通过 DataManager）加载，
    #     不需要从第三方数据源（DataSourceManager）获取数据。
        
    #     Args:
    #         scenario_name: 可选，如果提供则只执行指定的 scenario，否则执行所有 scenarios
    #     """
    #     # 1. 发现和验证所有 scenarios（调用 _discover_and_validate_scenarios）
    #     #    - 发现所有 scenarios
    #     #    - 验证所有 settings
    #     #    - 移除验证失败的 scenarios
    #     # 
    #     # 2. 执行 scenarios：
    #     #    - 如果 scenario_name 为 None，执行所有 scenarios
    #     #    - 如果 scenario_name 不为 None，只执行指定的 scenario
    #     #    - 对每个 scenario：
    #     #        a. 获取 worker 实例（自动创建并缓存）
    #     #        b. 调用 worker.run()（确保元信息存在）
    #     #        c. 执行多进程计算（TagManager 负责）
    #     #        c. 等待完成（同步）
    #     #        d. 如果出错，记录日志但继续执行其他 scenarios
        
    #     # 1. 发现和验证所有 scenarios
    #     self._discover_and_validate_scenarios()
        
    #     # 2. 确定要执行的 scenarios
    #     if scenario_name is not None:
    #         if scenario_name not in self.scenarios:
    #             raise ValueError(
    #                 f"Scenario '{scenario_name}' 不存在或验证失败。"
    #                 f"可用的 scenarios: {list(self.scenarios.keys())}"
    #             )
    #         scenarios_to_run = [scenario_name]
    #     else:
    #         scenarios_to_run = list(self.scenarios.keys())
        
    #     if len(scenarios_to_run) == 0:
    #         logger.warning("没有可用的 scenarios 需要执行")
    #         return
        
    #     # 3. 执行 scenarios
    #     for scenario_name in scenarios_to_run:
    #         try:
    #             # 获取 worker 实例（自动创建并缓存）
    #             worker = self.get_worker_instance(scenario_name)
    #             if worker is None:
    #                 logger.warning(f"无法创建 worker 实例: {scenario_name}，跳过")
    #                 continue
                
    #             # 调用 worker.run()（确保元信息存在）
    #             logger.info(f"开始执行 scenario: {scenario_name}")
    #             worker.run()
                
    #             # 执行多进程计算（TagManager 负责）
    #             self._execute_scenario(worker)
                
    #             logger.info(f"完成执行 scenario: {scenario_name}")
                
    #         except Exception as e:
    #             # 如果出错，记录日志但继续执行其他 scenarios
    #             logger.error(
    #                 f"执行 scenario '{scenario_name}' 时出错: {e}",
    #                 exc_info=True
    #             )
    #             continue
    
    # def _execute_scenario(self, worker: BaseTagWorker):
    #     """
    #     执行单个 scenario 的多进程计算
        
    #     Args:
    #         worker: BaseTagWorker 实例
    #     """
    #     # 1. 获取 scenario 和 tag definitions
    #     scenario, tag_defs = worker.ensure_metadata()
        
    #     # 2. 处理版本变更，获取日期范围
    #     version_action = worker.handle_version_change()
    #     start_date, end_date = worker.handle_update_mode(version_action)
        
    #     # 3. 获取实体列表
    #     entities = self._get_entity_list()
        
    #     if not entities:
    #         logger.warning(f"没有实体需要计算: scenario={worker.scenario_name}")
    #         return
        
    #     # 4. 构建 jobs（每个 entity 一个 job）
    #     jobs = self._build_entity_jobs(worker, entities, tag_defs, start_date, end_date)
        
    #     # 5. 决定进程数
    #     max_workers_config = worker.performance.get("max_workers")
    #     max_workers = self._decide_max_workers(len(jobs), max_workers_config)
        
    #     logger.info(
    #         f"开始多进程计算: scenario={worker.scenario_name}, "
    #         f"entities={len(entities)}, jobs={len(jobs)}, max_workers={max_workers}"
    #     )
        
    #     # 6. 使用 ProcessWorker 执行 jobs
    #     from utils.worker.multi_process.process_worker import ProcessWorker, ExecutionMode
        
    #     worker_pool = ProcessWorker(
    #         max_workers=max_workers,
    #         execution_mode=ExecutionMode.QUEUE,  # 队列模式，持续填充
    #         job_executor=TagManager._tag_worker_wrapper,  # 静态方法
    #         is_verbose=True
    #     )
        
    #     # 执行 jobs
    #     stats = worker_pool.run_jobs(jobs)
        
    #     # 7. 收集结果和统计信息
    #     successful_results = worker_pool.get_successful_results()
    #     failed_results = worker_pool.get_failed_results()
        
    #     # 统计信息
    #     total_tags = sum(
    #         r.result.get('total_tags', 0) 
    #         for r in successful_results 
    #         if r.result and isinstance(r.result, dict)
    #     )
        
    #     logger.info(
    #         f"Tag计算完成: scenario={worker.scenario_name}, "
    #         f"成功={len(successful_results)}, 失败={len(failed_results)}, "
    #         f"总tag数={total_tags}"
    #     )
        
    #     # 如果有失败的任务，记录详细信息
    #     if failed_results:
    #         logger.warning(f"有 {len(failed_results)} 个任务失败:")
    #         for failed in failed_results[:10]:  # 只显示前10个
    #             logger.warning(f"  - {failed.job_id}: {failed.error}")
        
    #     # 打印统计信息
    #     worker_pool.print_stats()
        
    #     # 注意：当前没有持久化结果收集器或缓存
    #     # 如果需要，可以在这里添加结果收集逻辑，例如：
    #     # - 将结果存储到数据库
    #     # - 缓存到内存（如果需要在后续步骤中使用）
    #     # - 写入文件或日志
    
    # def _build_entity_jobs(
    #     self,
    #     worker: BaseTagWorker,
    #     entities: List[str],
    #     tag_defs: List[Dict[str, Any]],
    #     start_date: str,
    #     end_date: str
    # ) -> List[Dict[str, Any]]:
    #     """
    #     构建 entity jobs（每个 entity 一个 job）
        
    #     Args:
    #         worker: BaseTagWorker 实例
    #         entities: 实体ID列表
    #         tag_defs: Tag Definition 列表
    #         start_date: 起始日期
    #         end_date: 结束日期
            
    #     Returns:
    #         List[Dict[str, Any]]: Job列表
    #     """
    #     jobs = []
        
    #     for entity_id in entities:
    #         job = {
    #             'id': f"{entity_id}_{worker.scenario_name}",
    #             'payload': {
    #                 'entity_id': entity_id,
    #                 'entity_type': 'stock',
    #                 'scenario_name': worker.scenario_name,
    #                 'scenario_version': worker.scenario_version,
    #                 'tag_definitions': tag_defs,
    #                 'tag_configs': worker.tags_config,
    #                 'start_date': start_date,
    #                 'end_date': end_date,
    #                 'base_term': worker.base_term,
    #                 'required_terms': worker.required_terms,
    #                 'required_data': worker.required_data,
    #                 'core': worker.core,
    #                 'worker_class': worker.__class__,  # 用于子进程实例化
    #                 'settings_path': worker.settings_path,
    #             }
    #         }
    #         jobs.append(job)
        
    #     return jobs
    
    # def _decide_max_workers(self, job_count: int, max_workers_config: Optional[int] = None) -> int:
    #     """
    #     根据 job 数量决定进程数（最多10个）
        
    #     策略：
    #     1. 如果配置了 max_workers，使用配置值（但不超过10）
    #     2. 如果 job 数量 <= 1，使用1个进程
    #     3. 如果 job 数量 <= 5，使用2个进程
    #     4. 如果 job 数量 <= 10，使用3个进程
    #     5. 如果 job 数量 <= 20，使用5个进程
    #     6. 如果 job 数量 <= 50，使用8个进程
    #     7. 否则使用10个进程（最大）
        
    #     Args:
    #         job_count: Job 数量
    #         max_workers_config: 配置的 max_workers 值
            
    #     Returns:
    #         int: 进程数
    #     """
    #     # 如果配置了 max_workers，优先使用（但不超过10）
    #     if max_workers_config is not None:
    #         return min(max_workers_config, 10)
        
    #     # 根据 job 数量决定
    #     if job_count <= 1:
    #         return 1
    #     elif job_count <= 5:
    #         return 2
    #     elif job_count <= 10:
    #         return 3
    #     elif job_count <= 20:
    #         return 5
    #     elif job_count <= 50:
    #         return 8
    #     else:
    #         return 10  # 最大10个进程
    
    # def _get_entity_list(self) -> List[str]:
    #     """
    #     获取实体列表（股票列表）
        
    #     目前只支持股票，未来可以扩展支持其他实体类型
        
    #     Returns:
    #         List[str]: 实体ID列表
    #     """
    #     # 从 DataManager 获取股票列表
    #     if not self.data_mgr:
    #         raise ValueError("DataManager 未初始化，无法获取实体列表")
        
    #     # 使用 DataManager 的 get_stock_list 方法
    #     if hasattr(self.data_mgr, "get_stock_list"):
    #         stock_list = self.data_mgr.get_stock_list()
    #         return [stock.get('id') for stock in stock_list if stock.get('id')]
        
    #     # 备用方案：使用 StockModel
    #     try:
    #         stock_model = self.data_mgr.get_model("stock")
    #         if stock_model:
    #             stocks = stock_model.get_all()
    #             return [stock.get('id') for stock in stocks if stock.get('id')]
    #     except Exception as e:
    #         logger.warning(f"获取股票列表失败: {e}")
        
    #     return []
    
    # def _discover_and_validate_scenarios(self):
    #     """
    #     发现和验证所有 scenarios
        
    #     统一入口：完成发现、注册、验证，并移除验证失败的 scenarios
        
    #     确保 self.scenarios 中只包含验证通过的可用 scenarios
    #     """
    #     # 1. 发现所有 scenarios（调用 _discover_and_register_workers）
    #     # 2. 验证所有 settings，移除验证失败的（调用 _validate_all_settings_and_remove_invalid）
        
    #     # 1. 发现所有 scenarios
    #     self._discover_and_register_workers()
        
    #     # 2. 验证所有 settings，移除验证失败的
    #     self._validate_all_settings_and_remove_invalid()
        
    #     # 确保 scenarios 中只包含验证通过的可用 scenarios
    #     logger.info(f"发现并验证完成，共有 {len(self.scenarios)} 个可用的 scenarios")
    
    # def _discover_and_register_workers(self):
    #     """
    #     发现所有 scenario workers（扫描静态 settings / modules）
        
    #     只做发现和加载，不注册到数据库
    #     """
    #     # 如果 scenarios 目录不存在，直接返回
    #     # 遍历 scenarios 目录下的所有子目录
    #     # 对每个子目录（scenario_name）：
    #     #   1. 检查 tag_worker.py 是否存在（递归查找）
    #     #   2. 检查 settings.py 是否存在（递归查找）
    #     #   3. 如果缺少文件，记录警告并跳过
    #     #   4. 加载 settings（调用 _load_settings）
    #     #   5. 加载 worker 类（调用 _load_worker）
    #     #   6. 调用统一的注册入口（register_scenario）
    #     #      - register_scenario 会检查 is_enabled 字段
    #     #      - register_scenario 会验证 settings 结构
    #     #      - register_scenario 会存储到字典
    #     #   注意：不在这里注册到数据库，延迟到 worker.run() 时
        
    #     if not FileUtil.dir_exists(str(self.scenarios_root)):
    #         logger.warning(f"Scenarios 目录不存在: {self.scenarios_root}")
    #         return
        
    #     # 遍历 scenarios 目录下的所有子目录
    #     for scenario_dir in self.scenarios_root.iterdir():
    #         if not scenario_dir.is_dir():
    #             continue
            
    #         scenario_name = scenario_dir.name
            
    #         # 1. 检查 tag_worker.py 是否存在（递归查找）
    #         worker_file_path = FileUtil.find_file_in_folder(
    #             "tag_worker.py",
    #             str(scenario_dir),
    #             is_recursively=True
    #         )
    #         if not worker_file_path:
    #             logger.warning(
    #                 f"Scenario '{scenario_name}' 缺少 tag_worker.py 文件，跳过"
    #             )
    #             continue
            
    #         # 2. 检查 settings.py 是否存在（递归查找）
    #         settings_file_path = FileUtil.find_file_in_folder(
    #             "settings.py",
    #             str(scenario_dir),
    #             is_recursively=True
    #         )
    #         if not settings_file_path:
    #             logger.warning(
    #                 f"Scenario '{scenario_name}' 缺少 settings.py 文件，跳过"
    #             )
    #             continue
            
    #         # 3. 加载 settings（调用 _load_settings）
    #         try:
    #             settings = self._load_settings(Path(settings_file_path))
    #         except Exception as e:
    #             logger.warning(
    #                 f"加载 scenario '{scenario_name}' 的 settings 失败: {e}，跳过",
    #                 exc_info=True
    #             )
    #             continue
            
    #         # 4. 加载 worker 类（调用 _load_worker）
    #         try:
    #             worker_class = self._load_worker(Path(worker_file_path))
    #         except Exception as e:
    #             logger.warning(
    #                 f"加载 scenario '{scenario_name}' 的 worker 失败: {e}，跳过",
    #                 exc_info=True
    #             )
    #             continue
            
    #         # 5. 调用统一的注册入口（register_scenario）
    #         try:
    #             self.register_scenario(
    #                 worker_class=worker_class,
    #                 settings_dict=settings,
    #                 scenario_name=scenario_name
    #             )
    #         except ValueError as e:
    #             # 验证失败，记录警告并跳过（不会添加到 scenarios 中）
    #             logger.warning(
    #                 f"注册 scenario '{scenario_name}' 失败: {e}，跳过"
    #             )
    #             continue
    #         except Exception as e:
    #             # 其他异常，记录错误并跳过（不会添加到 scenarios 中）
    #             logger.error(
    #                 f"注册 scenario '{scenario_name}' 时发生异常: {e}，跳过",
    #                 exc_info=True
    #             )
    #             continue
    
    # def _validate_all_settings_and_remove_invalid(self):
    #     """
    #     验证所有已注册 scenarios 的 settings，并移除验证失败的
        
    #     注意：基本结构验证已在 register_scenario 中完成，这里主要做额外的验证
    #     （如枚举值验证等）
        
    #     验证失败的 scenarios 会被从 self.scenarios 中移除
    #     """
    #     invalid_scenarios = []
        
    #     for scenario_name, scenario_info in list(self.scenarios.items()):
    #         settings = scenario_info["settings"]
    #         try:
    #             # 验证枚举值（使用 SettingsValidator）
    #             SettingsValidator.validate_enums(settings)
                
    #         except ValueError as e:
    #             # 如果验证失败，记录错误并标记为无效
    #             logger.error(f"验证 scenario '{scenario_name}' 的 settings 失败: {e}")
    #             invalid_scenarios.append(scenario_name)
    #         except Exception as e:
    #             # 其他异常
    #             logger.error(f"验证 scenario '{scenario_name}' 的 settings 时发生异常: {e}")
    #             invalid_scenarios.append(scenario_name)
        
    #     # 移除验证失败的 scenarios
    #     for scenario_name in invalid_scenarios:
    #         del self.scenarios[scenario_name]
    #         logger.warning(f"已移除验证失败的 scenario: {scenario_name}")
    
    # def register_scenario(
    #     self, 
    #     worker_class: Type[BaseTagWorker], 
    #     settings_dict: Dict[str, Any],
    #     scenario_name: str = None
    # ):
    #     """
    #     注册 scenario（统一入口）
        
    #     这是统一的注册入口，内部函数和外部 API 都调用此方法。
    #     完成所有验证和存储逻辑。
        
    #     Args:
    #         worker_class: Worker 类（继承自 BaseTagWorker）
    #         settings_dict: Settings 字典（格式同 settings.py 中的 Settings）
    #         scenario_name: Scenario 名称（可选，如果不提供，从 settings.scenario.name 获取）
            
    #     Raises:
    #         ValueError: 如果验证失败
            
    #     Note:
    #         - 如果 is_enabled=False，会记录信息并返回（不抛出异常）
    #         - 其他验证失败会抛出 ValueError
    #     """
    #     # 1. 验证 settings 基本结构
    #     if not isinstance(settings_dict, dict):
    #         raise ValueError(f"Settings 必须是字典类型，当前类型: {type(settings_dict)}")
        
    #     # 2. 获取 scenario_name（从参数或 settings 中获取）
    #     if scenario_name is None:
    #         if "scenario" not in settings_dict:
    #             raise ValueError("Settings 缺少 'scenario' 字段，无法获取 scenario_name")
    #         scenario = settings_dict["scenario"]
    #         if not isinstance(scenario, dict) or "name" not in scenario:
    #             raise ValueError("Settings.scenario 缺少 'name' 字段，无法获取 scenario_name")
    #         scenario_name = scenario["name"]
        
    #     # 3. 检查 is_enabled 字段
    #     if "is_enabled" not in settings_dict:
    #         raise ValueError(f"Scenario '{scenario_name}' 缺少 'is_enabled' 字段")
        
    #     if not settings_dict.get("is_enabled", False):
    #         logger.info(f"Scenario '{scenario_name}' 被禁用 (is_enabled=False)，跳过注册")
    #         return  # 不抛出异常，只是跳过
        
    #     # 4. 验证 settings 结构（调用 _validate_settings_structure）
    #     self._validate_settings_structure(scenario_name, settings_dict)
        
    #     # 5. 存储到字典
    #     self.scenarios[scenario_name] = {
    #         "worker_class": worker_class,
    #         "settings": settings_dict,
    #         "instance": None  # 实例缓存，延迟创建
    #     }
        
    #     # 创建 ScenarioIdentifier（用于日志和后续使用）
    #     scenario_id = ScenarioIdentifier.from_settings(settings_dict)
    #     logger.info(f"注册 scenario: {scenario_id}")
    
    # def _validate_settings_structure(self, scenario_name: str, settings: Dict[str, Any]):
    #     """
    #     验证 settings 结构（不包含 is_enabled 检查，因为已在 register_scenario 中检查）
        
    #     Args:
    #         scenario_name: Scenario 名称（用于错误信息）
    #         settings: Settings 字典
            
    #     Raises:
    #         ValueError: 如果验证失败
    #     """
    #     # 使用 SettingsValidator 进行验证
    #     # 注意：这里只做基本结构验证，枚举值验证在 _validate_all_settings_and_remove_invalid 中完成
    #     try:
    #         SettingsValidator.validate_scenario_fields(settings)
    #         SettingsValidator.validate_calculator_fields(settings)
    #         SettingsValidator.validate_tags_fields(settings)
    #     except ValueError as e:
    #         # 添加 scenario_name 前缀以便于调试
    #         raise ValueError(f"Scenario '{scenario_name}': {str(e)}")
    
    # def _load_settings(self, settings_file: Path) -> Dict[str, Any]:
    #     """
    #     加载 settings 文件
        
    #     Args:
    #         settings_file: settings.py 文件路径
            
    #     Returns:
    #         Dict[str, Any]: Settings 字典
            
    #     Raises:
    #         ValueError: settings 文件格式错误
    #     """
    #     # 使用 SettingsProcessor 读取 settings 文件
    #     # 注意：这里只做基本验证，详细验证在 register_scenario 中完成
    #     settings = SettingsProcessor.read_settings_file(
    #         str(settings_file),
    #         str(settings_file)  # worker_path 这里用同一个路径（TagManager 不需要）
    #     )
        
    #     return settings
    
    # def _load_worker(self, worker_file: Path) -> Type[BaseTagWorker]:
    #     """
    #     加载 worker 类
        
    #     Args:
    #         worker_file: tag_worker.py 文件路径
            
    #     Returns:
    #         Type[BaseTagWorker]: Worker 类
    #     """
    #     # 动态导入模块
    #     # 查找继承自 BaseTagWorker 的类
    #     # 返回 Worker 类
        
    #     # 动态导入模块
    #     spec = importlib.util.spec_from_file_location("tag_worker", worker_file)
    #     if spec is None or spec.loader is None:
    #         raise ValueError(f"无法加载 worker 文件: {worker_file}")
        
    #     module = importlib.util.module_from_spec(spec)
    #     try:
    #         spec.loader.exec_module(module)
    #     except SyntaxError as e:
    #         raise ValueError(f"Worker 文件语法错误: {worker_file}\n{str(e)}")
    #     except Exception as e:
    #         raise ValueError(f"导入 worker 文件失败: {worker_file}\n{str(e)}")
        
    #     # 查找继承自 BaseTagWorker 的类
    #     worker_class = None
    #     for name, obj in module.__dict__.items():
    #         if (isinstance(obj, type) and 
    #             issubclass(obj, BaseTagWorker) and 
    #             obj != BaseTagWorker):
    #             worker_class = obj
    #             break
        
    #     if worker_class is None:
    #         raise ValueError(
    #             f"Worker 文件中没有找到继承自 BaseTagWorker 的类: {worker_file}"
    #         )
        
    #     return worker_class
    
    # # ========================================================================
    # # Worker 管理（自动创建实例）
    # # ========================================================================
    
    # def get_worker(self, scenario_name: str) -> Optional[Type[BaseTagWorker]]:
    #     """
    #     获取指定 scenario 的 worker 类
        
    #     Args:
    #         scenario_name: scenario 名称（目录名）
            
    #     Returns:
    #         Type[BaseTagWorker] 或 None
    #     """
    #     # 从 self.scenarios 字典中获取
    #     scenario_info = self.scenarios.get(scenario_name)
    #     if scenario_info:
    #         return scenario_info.get("worker_class")
    #     return None
    
    # def get_worker_instance(
    #     self,
    #     scenario_name: str
    # ) -> Optional[BaseTagWorker]:
    #     """
    #     获取指定 scenario 的 worker 实例（自动创建并缓存）
        
    #     TagManager 自动管理 worker 实例的创建和缓存
        
    #     Args:
    #         scenario_name: scenario 名称（目录名）
            
    #     Returns:
    #         BaseTagWorker 实例或 None
    #     """
    #     # 1. 获取 scenario 信息
    #     scenario_info = self.scenarios.get(scenario_name)
    #     if scenario_info is None:
    #         return None
        
    #     # 2. 检查缓存
    #     if scenario_info["instance"] is not None:
    #         return scenario_info["instance"]
        
    #     # 3. 获取 worker 类和 settings
    #     worker_class = scenario_info["worker_class"]
    #     settings = scenario_info["settings"]
        
    #     # 4. 确定 settings 文件路径
    #     # 注意：这里需要找到实际的 settings 文件路径
    #     # 由于我们在 _discover_and_register_workers 中已经加载了 settings
    #     # 这里可以使用相对路径或绝对路径
    #     # 为了简化，我们使用相对路径（相对于 scenario 目录）
    #     settings_path = "settings.py"  # 相对于 tag_worker 同级目录
        
    #     # 5. 创建 worker 实例
    #     try:
    #         worker = worker_class(
    #             settings_path=settings_path,
    #             data_mgr=self.data_mgr,
    #             tag_data_service=self.tag_data_service
    #         )
            
    #         # 6. 缓存到 scenario_info
    #         scenario_info["instance"] = worker
            
    #         return worker
    #     except Exception as e:
    #         logger.error(
    #             f"创建 worker 实例失败: {scenario_name}, 错误: {e}",
    #             exc_info=True
    #         )
    #         return None
    
    # def list_scenarios(self) -> List[str]:
    #     """
    #     列出所有可用的 scenario 名称
        
    #     Returns:
    #         List[str]: scenario 名称列表
    #     """
    #     # 返回 self.scenarios 字典的所有键
    #     return list(self.scenarios.keys())
    
    # def reload(self):
    #     """
    #     重新发现所有 scenarios
        
    #     用于动态加载新添加的 scenario
    #     """
    #     # 清空字典
    #     # 调用 _discover_and_register_workers()
        
    #     self.scenarios.clear()
    #     self._discover_and_register_workers()
    
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
                - settings_path: Settings 文件路径
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        # 1. 初始化 DataManager 和 TagDataService（子进程中）
        from app.data_manager import DataManager
        data_mgr = DataManager(is_verbose=False)
        tag_data_service = data_mgr.get_tag_service()
        
        # 2. 获取 worker 类和 settings 路径
        worker_class = payload['worker_class']
        settings_path = payload['settings_path']
        
        # 3. 创建 worker 实例（子进程中）
        # 注意：worker 实例化时会从 settings 自动加载所有配置
        # （base_term, required_terms, required_data, core, tags_config 等）
        worker = worker_class(
            settings_path=settings_path,
            data_mgr=data_mgr,
            tag_data_service=tag_data_service
        )
        
        # 4. 调用 process_entity 方法
        return worker.process_entity(payload)
