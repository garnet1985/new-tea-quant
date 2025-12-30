"""
Tag Calculator 基类

职责：
1. 执行流程（run 方法，包含 ensure_metadata 和 renew_or_create_values）
2. 元信息管理（ensure_scenario, ensure_tags）
3. 版本变更处理（handle_version_change, handle_update_mode）
4. 数据加载（钩子函数，默认实现支持股票，从数据库加载）
5. 计算钩子（calculate_tag，用户实现）
6. 其他钩子（初始化、清理、错误处理）

注意：
- Tag 系统是预计算系统，数据应该从数据库（通过 DataManager）加载
- 不使用第三方数据源（DataSourceManager）
- 配置验证和处理逻辑已提取到 settings_validator 和 settings_processor
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple, Type
import inspect
import logging
from app.tag.enums import UpdateMode, VersionChangeAction
from app.tag.config import ALLOW_VERSION_ROLLBACK
from app.tag.settings_validator import SettingsValidator
from app.tag.settings_processor import SettingsProcessor

logger = logging.getLogger(__name__)


class BaseTagCalculator(ABC):
    """
    Tag Calculator 基类
    
    职责：
    1. 执行流程（run 方法，包含 ensure_metadata 和 renew_or_create_values）
    2. 元信息管理（ensure_scenario, ensure_tags）
    3. 版本变更处理（handle_version_change, handle_update_mode）
    4. 数据加载（钩子函数，默认实现支持股票，从数据库加载）
    5. 计算钩子（calculate_tag，用户实现）
    6. 其他钩子（初始化、清理、错误处理）
    
    注意：
    - Tag 系统是预计算系统，数据应该从数据库（通过 DataManager）加载
    - 不使用第三方数据源（DataSourceManager）
    """
    
    def __init__(
        self, 
        settings_path: str,
        data_mgr=None,
        tag_service=None
    ):
        """
        初始化 Calculator
        
        Args:
            settings_path: settings 文件路径（相对于 calculator 同级目录）
            data_mgr: DataManager 实例（用于访问数据库模型）
            tag_service: TagService 实例（用于访问 tag 相关的数据库操作）
        """
        self.settings_path = settings_path
        self.data_mgr = data_mgr
        self.tag_service = tag_service
        
        # 如果 tag_service 为 None，从 data_mgr 获取
        if self.tag_service is None and self.data_mgr is not None:
            self.tag_service = self.data_mgr.get_tag_service()
        
        # 获取 calculator 文件路径（用于确定 settings 的相对路径）
        calculator_file = inspect.getfile(self.__class__)
        
        # 读取、验证和处理配置（使用 helper）
        self.settings = SettingsProcessor.load_and_process_settings(
            settings_path, calculator_file
        )
        SettingsValidator.validate_all(self.settings)
        
        # 提取 calculator 配置到实例变量
        config = SettingsProcessor.extract_calculator_config(self.settings)
        self.scenario_name = config["scenario_name"]
        self.scenario_version = config["scenario_version"]
        self.base_term = config["base_term"]
        self.required_terms = config["required_terms"]
        self.required_data = config["required_data"]
        self.core = config["core"]
        self.performance = config["performance"]
        
        # 处理 tags 配置（合并、验证）
        self.tags_config = SettingsProcessor.process_tags_config(
            self.settings["tags"],
            self.settings["calculator"]
        )
        
        # 初始化 tracker：用于存储计算过程中的临时状态
        # tracker 只在当前 calculator 实例的生命周期内存在
        # 在多进程环境下，每个子进程有独立的 calculator 实例，因此 tracker 也是独立的
        # 用户可以在 calculate_tag 等方法中使用 self.tracker 来存储和读取临时变量
        self.tracker: Dict[str, Any] = {}
        
        # 初始化（钩子函数）
        self.on_init()
    
    # ========================================================================
    # 1. 数据加载（钩子函数，默认实现支持股票）
    # ========================================================================
    
    def load_entity_data(
        self,
        entity_id: str,
        entity_type: str = "stock",
        as_of_date: str = None
    ) -> Dict[str, Any]:
        """
        加载实体历史数据（默认实现支持股票）
        
        用户可以重写此方法以支持自定义数据源
        
        Args:
            entity_id: 实体ID（如股票代码 "000001.SZ"）
            entity_type: 实体类型（默认 "stock"）
            as_of_date: 截止日期（格式：YYYYMMDD，如果为 None，使用最新日期）
            
        Returns:
            Dict[str, Any]: 历史数据字典
                {
                    "klines": {
                        "daily": [...],
                        "weekly": [...],
                        ...
                    },
                    "finance": {...},
                    ...
                }
        """
        if not self.data_mgr:
            raise ValueError("DataManager 未初始化，无法加载数据")
        
        historical_data = {}
        
        # 1. 加载 K 线数据
        kline_terms = set([self.base_term] + (self.required_terms or []))
        klines = {}
        
        for term in kline_terms:
            try:
                if hasattr(self.data_mgr, "load_kline"):
                    kline_data = self.data_mgr.load_kline(
                        entity_id=entity_id,
                        term=term,
                        end_date=as_of_date
                    )
                else:
                    # 备用方案：使用 model
                    kline_model = self.data_mgr.get_model(f"stock_kline_{term}")
                    if kline_model:
                        kline_data = kline_model.load_by_stock(entity_id, end_date=as_of_date)
                    else:
                        kline_data = []
                klines[term] = kline_data
            except Exception as e:
                logger.warning(f"加载 {term} K线数据失败: {entity_id}, 错误: {e}")
                klines[term] = []
        
        historical_data["klines"] = klines
        
        # 2. 加载其他数据源
        for data_source in self.required_data:
            if data_source == "corporate_finance":
                try:
                    if hasattr(self.data_mgr, "load_corporate_finance"):
                        finance_data = self.data_mgr.load_corporate_finance(
                            entity_id=entity_id,
                            end_date=as_of_date
                        )
                    else:
                        # 备用方案：使用 model
                        finance_model = self.data_mgr.get_model("corporate_finance")
                        if finance_model:
                            finance_data = finance_model.load_by_stock(entity_id, end_date=as_of_date)
                        else:
                            finance_data = {}
                    historical_data["finance"] = finance_data
                except Exception as e:
                    logger.warning(f"加载财务数据失败: {entity_id}, 错误: {e}")
                    historical_data["finance"] = {}
        
        return historical_data
    
    # ========================================================================
    # 2. 计算执行（用户实现）
    # ========================================================================
    
    @abstractmethod
    def calculate_tag(
        self,
        entity_id: str,
        entity_type: str,
        as_of_date: str,
        historical_data: Dict[str, Any],
        tag_config: Dict[str, Any]
    ) -> Optional[Any]:
        """
        计算 tag（用户实现）
        
        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            as_of_date: 业务日期（格式：YYYYMMDD）
            historical_data: 历史数据字典
            tag_config: 当前 tag 的配置（已合并 calculator 和 tag 配置）
                - base_term: 基础周期
                - required_terms: 需要的周期列表
                - required_data: 需要的数据源列表
                - core: calculator 的 core 参数（所有 tags 共享）
                - performance: calculator 的 performance 配置（所有 tags 共享）
                - tag_meta: tag 元信息（name, display_name, description）
        
        Returns:
            Dict[str, Any] 或 None:
                - 如果返回 None，不创建 tag
                - 如果返回字典，格式：
                    {
                        "value": str,  # 标签值（字符串）
                        "start_date": str,  # 可选，起始日期（YYYYMMDD）
                        "end_date": str,  # 可选，结束日期（YYYYMMDD）
                    }
        """
        pass
    
    # ========================================================================
    # 3. Tag 值保存（通过 TagService）
    # ========================================================================
    
    def save_tag_value(
        self,
        tag_definition_id: int,
        entity_id: str,
        entity_type: str,
        as_of_date: str,
        value: str,
        start_date: str = None,
        end_date: str = None
    ):
        """
        保存 tag 值到数据库（通过 TagService）
        
        Args:
            tag_definition_id: Tag Definition ID
            entity_id: 实体ID
            entity_type: 实体类型
            as_of_date: 业务日期
            value: 标签值（字符串）
            start_date: 起始日期（可选）
            end_date: 结束日期（可选）
        """
        if not self.tag_service:
            raise ValueError("TagService 未初始化，无法保存 tag 值")
        
        self.tag_service.save_tag_value(
            tag_definition_id=tag_definition_id,
            entity_id=entity_id,
            entity_type=entity_type,
            as_of_date=as_of_date,
            value=value,
            start_date=start_date,
            end_date=end_date
        )
    
    # ========================================================================
    # 4. 执行入口（Calculator 入口函数）
    # ========================================================================
    
    def run(self):
        """
        Calculator 入口函数（由 TagManager.run() 调用）
        
        流程：
        1. 确保元信息存在（ensure_metadata）
        2. 处理版本变更和更新模式（renew_or_create_values）
        """
        # 1. 确保元信息存在
        scenario, tag_defs = self.ensure_metadata()
        
        # 2. 处理版本变更和更新模式
        self.renew_or_create_values()
    
    def ensure_metadata(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        确保元信息存在（scenario 和 tag definitions）
        
        Returns:
            Tuple[Dict[str, Any], List[Dict[str, Any]]]: (scenario, tag_definitions)
        """
        # 1. 确保 scenario 存在
        scenario = self.ensure_scenario()
        
        # 2. 确保 tag definitions 存在
        tag_defs = self.ensure_tags(scenario)
        
        return scenario, tag_defs
    
    def ensure_scenario(self) -> Dict[str, Any]:
        """
        确保 scenario 存在（如果不存在则创建）
        
        Returns:
            Dict[str, Any]: Scenario 记录
        """
        if not self.tag_service:
            raise ValueError("TagService 未初始化，无法确保 scenario 存在")
        
        # 1. 查询数据库中该 scenario name 的所有版本
        existing_scenarios = self.tag_service.list_scenarios(
            scenario_name=self.scenario_name
        )
        
        # 2. 查找 settings.version 是否已存在
        target_scenario = None
        for s in existing_scenarios:
            if s.get("version") == self.scenario_version:
                target_scenario = s
                break
        
        # 3. 如果已存在，返回该 scenario
        if target_scenario:
            return target_scenario
        
        # 4. 如果不存在，创建新的 scenario（通过 TagService）
        scenario_id = self.tag_service.create_scenario(
            name=self.scenario_name,
            version=self.scenario_version,
            display_name=self.settings["scenario"].get("display_name", self.scenario_name),
            description=self.settings["scenario"].get("description", "")
        )
        target_scenario = self.tag_service.get_scenario(self.scenario_name, self.scenario_version)
        
        # 5. 返回 scenario
        return target_scenario
    
    def ensure_tags(self, scenario: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        确保 tag definitions 存在（如果不存在则创建）
        
        Args:
            scenario: Scenario 记录
            
        Returns:
            List[Dict[str, Any]]: Tag Definition 列表
        """
        if not self.tag_service:
            raise ValueError("TagService 未初始化，无法确保 tags 存在")
        
        scenario_id = scenario["id"]
        
        # 1. 查询该 scenario 下的所有 tag definitions
        existing_tags = self.tag_service.get_tag_definitions(scenario_id=scenario_id)
        existing_tag_names = {tag["name"] for tag in existing_tags}
        
        # 2. 对每个 settings.tags 中的 tag：
        tag_definitions = []
        for tag_config in self.settings["tags"]:
            tag_name = tag_config["name"]
            
            # 检查是否已存在
            if tag_name in existing_tag_names:
                # 已存在，从 existing_tags 中获取
                for tag in existing_tags:
                    if tag["name"] == tag_name:
                        tag_definitions.append(tag)
                        break
            else:
                # 不存在，创建新的 tag definition
                tag_definition_id = self.tag_service.create_tag_definition(
                    scenario_id=scenario_id,
                    scenario_version=self.scenario_version,
                    name=tag_name,
                    display_name=tag_config["display_name"],
                    description=tag_config.get("description", "")
                )
                # 获取新创建的 tag definition
                new_tag = self.tag_service.get_tag_definitions(scenario_id=scenario_id, include_legacy=False)
                for tag in new_tag:
                    if tag["name"] == tag_name:
                        tag_definitions.append(tag)
                        break
        
        # 3. 返回 tag definitions 列表
        return tag_definitions
    
    def renew_or_create_values(self):
        """
        处理版本变更和更新模式
        
        流程：
        1. 处理版本变更（handle_version_change）
        2. 根据版本变更结果和 update_mode 计算（handle_update_mode）
        """
        # 1. 处理版本变更
        version_action = self.handle_version_change()
        
        # 2. 根据版本变更结果和 update_mode 计算
        self.handle_update_mode(version_action)
    
    def handle_version_change(self) -> str:
        """
        处理版本变更
        
        逻辑：
        1. 如果 settings.version 在数据库中已存在且 is_legacy=0（active）：
           - version_action = "NO_CHANGE"（版本未变，继续使用）
        2. 如果 settings.version 在数据库中已存在但 is_legacy=1（legacy）：
           - 这是用户把 version 改回到以前存在过的版本（版本回退）
           - 检查全局配置 ALLOW_VERSION_ROLLBACK
           - 如果 False：抛出 ValueError
           - 如果 True：标记旧的 active 为 legacy，设置当前为 active，version_action = "ROLLBACK"
        3. 如果 settings.version 在数据库中不存在：
           - 读取 on_version_change 配置
           - version_action = on_version_change（REFRESH_SCENARIO 或 NEW_SCENARIO）
           - 根据 version_action 处理
        
        Returns:
            str: VersionAction ("NO_CHANGE", "ROLLBACK", "NEW_SCENARIO", "REFRESH_SCENARIO")
        """
        if not self.tag_service:
            raise ValueError("TagService 未初始化，无法处理版本变更")
        
        # 1. 查询数据库中该 scenario name 的所有版本
        db_scenarios = self.tag_service.list_scenarios(
            scenario_name=self.scenario_name
        )
        
        # 2. 查找 settings.version 是否在数据库中已存在
        existing_scenario = None
        for s in db_scenarios:
            if s.get("version") == self.scenario_version:
                existing_scenario = s
                break
        
        # 3. 如果已存在且 is_legacy=0（active）：
        if existing_scenario and existing_scenario.get("is_legacy", 0) == 0:
            return "NO_CHANGE"
        
        # 4. 如果已存在但 is_legacy=1（legacy）：
        if existing_scenario and existing_scenario.get("is_legacy", 0) == 1:
            # 这是用户把 version 改回到以前存在过的版本（版本回退）
            # 检查全局配置 ALLOW_VERSION_ROLLBACK
            if not ALLOW_VERSION_ROLLBACK:
                error_msg = (
                    f"Version rollback detected but not allowed: "
                    f"scenario={self.scenario_name}, version={self.scenario_version}. "
                    "Version rollback may cause data inconsistency. "
                    "Only rollback version if calculator logic is also rolled back. "
                    "To allow version rollback, set ALLOW_VERSION_ROLLBACK=True in app/tag/config.py"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # ALLOW_VERSION_ROLLBACK = True
            warning_msg = (
                f"Version rollback detected: "
                f"scenario={self.scenario_name}, version={self.scenario_version}. "
                "WARNING: Version rollback may cause data inconsistency. "
                "Only rollback version if calculator logic is also rolled back. "
                "User is responsible for ensuring algorithm consistency."
            )
            logger.warning(warning_msg)
            
            # 查找当前的 active 版本（is_legacy=0）
            active_scenario = None
            for s in db_scenarios:
                if s.get("is_legacy", 0) == 0:
                    active_scenario = s
                    break
            
            # 如果存在 active 版本，标记为 legacy
            if active_scenario:
                self.tag_service.mark_scenario_as_legacy(active_scenario["id"])
            
            # 把当前版本（existing_scenario）设置为 legacy=0（active）
            self.tag_service.update_scenario(
                existing_scenario["id"],
                is_legacy=0
            )
            
            # 注意：不删除旧的 tag definitions 和 tag values
            # 确保 tag definitions 存在（调用 ensure_tags，如果不存在则创建）
            scenario = self.tag_service.get_scenario(self.scenario_name, self.scenario_version)
            self.ensure_tags(scenario)
            
            return "ROLLBACK"
        
        # 5. 如果不存在：
        # 读取 on_version_change 配置
        on_version_change = self.settings["scenario"].get(
            "on_version_change",
            VersionChangeAction.REFRESH_SCENARIO.value
        )
        
        if on_version_change == VersionChangeAction.NEW_SCENARIO.value:
            # NEW_SCENARIO：创建新 scenario，保留旧的
            # 查找当前的 active 版本（is_legacy=0）
            active_scenario = None
            for s in db_scenarios:
                if s.get("is_legacy", 0) == 0:
                    active_scenario = s
                    break
            
            # 如果存在 active 版本，标记为 legacy
            if active_scenario:
                self.tag_service.mark_scenario_as_legacy(active_scenario["id"])
            
            # 创建新 scenario
            scenario_id = self.tag_service.create_scenario(
                name=self.scenario_name,
                version=self.scenario_version,
                display_name=self.settings["scenario"].get("display_name", self.scenario_name),
                description=self.settings["scenario"].get("description", "")
            )
            
            # 清理旧版本
            self.cleanup_legacy_versions(self.scenario_name, keep_n=3)
            
            return "NEW_SCENARIO"
        
        elif on_version_change == VersionChangeAction.REFRESH_SCENARIO.value:
            # REFRESH_SCENARIO：删除之前结果，重新计算
            # 查找当前的 active 版本（is_legacy=0）
            active_scenario = None
            for s in db_scenarios:
                if s.get("is_legacy", 0) == 0:
                    active_scenario = s
                    break
            
            if active_scenario:
                # 更新 scenario（更新 version 等字段）
                self.tag_service.update_scenario(
                    active_scenario["id"],
                    display_name=self.settings["scenario"].get("display_name", self.scenario_name),
                    description=self.settings["scenario"].get("description", "")
                )
                # 删除旧的 tag definitions 和 tag values
                self.tag_service.delete_tag_definitions_by_scenario(active_scenario["id"])
                self.tag_service.delete_tag_values_by_scenario(active_scenario["id"])
            else:
                # 如果不存在 active 版本，创建新 scenario
                self.tag_service.create_scenario(
                    name=self.scenario_name,
                    version=self.scenario_version,
                    display_name=self.settings["scenario"].get("display_name", self.scenario_name),
                    description=self.settings["scenario"].get("description", "")
                )
            
            # 创建新的 tag definitions（调用 ensure_tags）
            scenario = self.tag_service.get_scenario(self.scenario_name, self.scenario_version)
            self.ensure_tags(scenario)
            
            return "REFRESH_SCENARIO"
        
        else:
            raise ValueError(f"未知的 on_version_change 值: {on_version_change}")
    
    def handle_update_mode(self, version_action: str):
        """
        根据版本变更结果和 update_mode 计算（多进程版本）
        
        Args:
            version_action: VersionAction ("NO_CHANGE", "ROLLBACK", "NEW_SCENARIO", "REFRESH_SCENARIO")
        """
        # 1. 获取 scenario 和 tag definitions
        scenario = self.ensure_scenario()
        tag_defs = self.ensure_tags(scenario)
        
        # 2. 确定计算日期范围
        start_date, end_date = self._determine_date_range(version_action, tag_defs)
        
        # 3. 获取实体列表
        entities = self._get_entity_list()
        
        if not entities:
            logger.warning(f"没有实体需要计算: scenario={self.scenario_name}")
            return
        
        # 4. 分割jobs（每个entity一个job）
        jobs = self._build_entity_jobs(entities, tag_defs, start_date, end_date)
        
        # 5. 决定进程数
        max_workers_config = self.performance.get("max_workers")
        max_workers = self._decide_max_workers(len(jobs), max_workers_config)
        
        logger.info(
            f"开始多进程计算: scenario={self.scenario_name}, "
            f"entities={len(entities)}, jobs={len(jobs)}, max_workers={max_workers}"
        )
        
        # 6. 使用ProcessWorker执行jobs
        from utils.worker.multi_process.process_worker import ProcessWorker, ExecutionMode
        
        worker = ProcessWorker(
            max_workers=max_workers,
            execution_mode=ExecutionMode.QUEUE,  # 队列模式，持续填充
            job_executor=BaseTagCalculator._process_single_entity_job,  # 静态方法
            is_verbose=True
        )
        
        # 执行jobs
        stats = worker.run_jobs(jobs)
        
        # 7. 收集结果和统计信息
        successful_results = worker.get_successful_results()
        failed_results = worker.get_failed_results()
        
        logger.info(
            f"Tag计算完成: scenario={self.scenario_name}, "
            f"成功={len(successful_results)}, 失败={len(failed_results)}"
        )
        
        # 打印统计信息
        worker.print_stats()
    
    def _determine_date_range(
        self, 
        version_action: str, 
        tag_defs: List[Dict[str, Any]]
    ) -> Tuple[str, str]:
        """
        确定计算日期范围
        
        Args:
            version_action: VersionAction
            tag_defs: Tag Definition 列表
            
        Returns:
            Tuple[str, str]: (start_date, end_date)
        """
        update_mode = self.performance.get("update_mode", UpdateMode.INCREMENTAL.value)
        
        if version_action == "NO_CHANGE":
            # 按 update_mode 计算
            if update_mode == UpdateMode.INCREMENTAL.value:
                # 从上次计算的最大 as_of_date 继续
                start_date = self._get_max_as_of_date(tag_defs)
                if start_date:
                    # 获取下一个交易日
                    start_date = self._get_next_trading_date(start_date)
                else:
                    # 如果没有历史数据，从 start_date 开始
                    start_date = self.settings["calculator"].get("start_date") or self._get_default_start_date()
                end_date = self.settings["calculator"].get("end_date") or self._get_latest_trading_date()
            elif update_mode == UpdateMode.REFRESH.value:
                # 从 start_date 到 end_date
                start_date = self.settings["calculator"].get("start_date") or self._get_default_start_date()
                end_date = self.settings["calculator"].get("end_date") or self._get_latest_trading_date()
            else:
                raise ValueError(f"未知的 update_mode: {update_mode}")
        
        elif version_action == "ROLLBACK":
            # 版本回退：按照该版本的 update_mode 继续
            logger.warning(
                f"Version rollback detected: scenario={self.scenario_name}, "
                f"version={self.scenario_version}. "
                f"Continuing with update_mode={update_mode}. "
                f"User is responsible for ensuring algorithm consistency."
            )
            if update_mode == UpdateMode.INCREMENTAL.value:
                # 从上次计算的最大 as_of_date 继续
                start_date = self._get_max_as_of_date(tag_defs)
                if start_date:
                    start_date = self._get_next_trading_date(start_date)
                else:
                    start_date = self.settings["calculator"].get("start_date") or self._get_default_start_date()
                end_date = self.settings["calculator"].get("end_date") or self._get_latest_trading_date()
            elif update_mode == UpdateMode.REFRESH.value:
                # 重新计算所有数据
                start_date = self.settings["calculator"].get("start_date") or self._get_default_start_date()
                end_date = self.settings["calculator"].get("end_date") or self._get_latest_trading_date()
            else:
                raise ValueError(f"未知的 update_mode: {update_mode}")
        
        else:
            # version_action == "NEW_SCENARIO" 或 "REFRESH_SCENARIO"
            # 重新计算所有 tags
            start_date = self.settings["calculator"].get("start_date") or self._get_default_start_date()
            end_date = self.settings["calculator"].get("end_date") or self._get_latest_trading_date()
        
        return start_date, end_date
    
    def _build_entity_jobs(
        self, 
        entities: List[str], 
        tag_defs: List[Dict[str, Any]], 
        start_date: str, 
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        构建entity jobs（每个entity一个job）
        
        Args:
            entities: 实体ID列表
            tag_defs: Tag Definition 列表
            start_date: 起始日期
            end_date: 结束日期
            
        Returns:
            List[Dict[str, Any]]: Job列表
        """
        jobs = []
        
        for entity_id in entities:
            job = {
                'id': f"{entity_id}_{self.scenario_name}",
                'payload': {
                    'entity_id': entity_id,
                    'entity_type': 'stock',
                    'scenario_name': self.scenario_name,
                    'scenario_version': self.scenario_version,
                    'tag_definitions': tag_defs,
                    'tag_configs': self.tags_config,
                    'start_date': start_date,
                    'end_date': end_date,
                    'base_term': self.base_term,
                    'required_terms': self.required_terms,
                    'required_data': self.required_data,
                    'core': self.core,
                    'calculator_class': self.__class__,
                    'settings_path': self.settings_path,
                }
            }
            jobs.append(job)
        
        return jobs
    
    def _decide_max_workers(self, job_count: int, max_workers_config: Optional[int] = None) -> int:
        """
        根据job数量决定进程数（最多10个）
        
        策略：
        1. 如果配置了max_workers，使用配置值（但不超过10）
        2. 如果job数量 <= 1，使用1个进程
        3. 如果job数量 <= 5，使用2个进程
        4. 如果job数量 <= 10，使用3个进程
        5. 如果job数量 <= 20，使用5个进程
        6. 如果job数量 <= 50，使用8个进程
        7. 否则使用10个进程（最大）
        
        Args:
            job_count: Job数量
            max_workers_config: 配置的max_workers值
            
        Returns:
            int: 进程数
        """
        # 如果配置了max_workers，优先使用（但不超过10）
        if max_workers_config is not None:
            return min(max_workers_config, 10)
        
        # 根据job数量决定
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
    
    @staticmethod
    def _process_single_entity_job(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        子进程执行函数：处理单个entity的tag计算（静态方法）
        
        流程：
        1. 初始化DataManager和TagService（子进程中）
        2. 加载entity的全量数据（子进程中，到end_date）
        3. 对每个as_of_date：
           a. 过滤数据到as_of_date（保证一致性，不包含未来数据）
           b. 对每个tag计算
           c. 收集结果
        4. 批量存储结果
        5. 返回统计信息
        
        注意：
        - 数据加载在子进程中进行，保证内存可控
        - 数据过滤到as_of_date，保证计算一致性（避免"上帝模式"问题）
        - 批量存储，提高性能
        - 进程结束自动释放内存
        
        Args:
            payload: Job payload字典
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        entity_id = payload['entity_id']
        scenario_name = payload['scenario_name']
        
        try:
            # 1. 初始化DataManager和TagService（子进程中）
            from app.data_manager import DataManager
            data_mgr = DataManager(is_verbose=False)
            tag_service = data_mgr.get_tag_service()
            
            # 2. 加载全量数据（子进程中，到end_date）
            historical_data = BaseTagCalculator._load_entity_data_in_process(
                entity_id=payload['entity_id'],
                entity_type=payload['entity_type'],
                base_term=payload['base_term'],
                required_terms=payload['required_terms'],
                required_data=payload['required_data'],
                as_of_date=payload['end_date'],  # 加载到end_date的全量数据
                data_mgr=data_mgr
            )
            
            # 3. 创建calculator实例（子进程中）
            calculator = BaseTagCalculator._create_calculator_instance_in_process(
                calculator_class=payload['calculator_class'],
                settings_path=payload['settings_path'],
                data_mgr=data_mgr,
                tag_service=tag_service
            )
            
            # 4. 获取交易日列表
            trading_dates = BaseTagCalculator._get_trading_dates_static(
                payload['start_date'],
                payload['end_date'],
                data_mgr
            )
            
            # 5. 计算tags
            results = []
            tag_definitions = payload['tag_definitions']
            tag_configs = payload['tag_configs']
            
            for as_of_date in trading_dates:
                # 过滤数据到as_of_date（保证一致性）
                filtered_data = BaseTagCalculator._filter_data_to_date(
                    historical_data, 
                    as_of_date
                )
                
                # 对每个tag计算
                for tag_def, tag_config in zip(tag_definitions, tag_configs):
                    try:
                        # 调用calculate_tag
                        result = calculator.calculate_tag(
                            entity_id=entity_id,
                            entity_type=payload['entity_type'],
                            as_of_date=as_of_date,
                            historical_data=filtered_data,  # 已过滤
                            tag_config=tag_config
                        )
                        
                        if result is not None:
                            if isinstance(result, dict):
                                results.append({
                                    'tag_definition_id': tag_def['id'],
                                    'entity_id': entity_id,
                                    'entity_type': payload['entity_type'],
                                    'as_of_date': as_of_date,
                                    'value': str(result.get('value', '')),
                                    'start_date': result.get('start_date'),
                                    'end_date': result.get('end_date'),
                                })
                    except Exception as e:
                        # 调用on_calculate_error钩子
                        calculator.on_calculate_error(entity_id, as_of_date, e)
                        
                        # 根据should_continue_on_error决定是否继续
                        if not calculator.should_continue_on_error():
                            raise
            
            # 6. 批量存储结果
            if results:
                BaseTagCalculator._batch_save_tag_values(results, tag_service)
            
            # 7. 返回统计信息
            return {
                'entity_id': entity_id,
                'total_tags': len(results),
                'success': True
            }
            
        except Exception as e:
            logger.exception(
                f"子进程执行失败: entity_id={entity_id}, scenario={scenario_name}, error={e}"
            )
            return {
                'entity_id': entity_id,
                'total_tags': 0,
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def _load_entity_data_in_process(
        entity_id: str,
        entity_type: str,
        base_term: str,
        required_terms: List[str],
        required_data: List[str],
        as_of_date: str,
        data_mgr
    ) -> Dict[str, Any]:
        """
        在子进程中加载entity数据（静态方法）
        
        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            base_term: 基础周期
            required_terms: 需要的其他周期
            required_data: 需要的数据源
            as_of_date: 截止日期
            data_mgr: DataManager实例
            
        Returns:
            Dict[str, Any]: 历史数据字典
        """
        historical_data = {}
        
        # 1. 加载K线数据
        kline_terms = set([base_term] + (required_terms or []))
        klines = {}
        
        for term in kline_terms:
            try:
                if hasattr(data_mgr, "load_kline"):
                    kline_data = data_mgr.load_kline(
                        entity_id=entity_id,
                        term=term,
                        end_date=as_of_date
                    )
                else:
                    # 备用方案：使用model
                    kline_model = data_mgr.get_model(f"stock_kline_{term}")
                    if kline_model:
                        kline_data = kline_model.load_by_stock(entity_id, end_date=as_of_date)
                    else:
                        kline_data = []
                klines[term] = kline_data
            except Exception as e:
                logger.warning(f"加载 {term} K线数据失败: {entity_id}, 错误: {e}")
                klines[term] = []
        
        historical_data["klines"] = klines
        
        # 2. 加载其他数据源
        for data_source in required_data:
            if data_source == "corporate_finance":
                try:
                    if hasattr(data_mgr, "load_corporate_finance"):
                        finance_data = data_mgr.load_corporate_finance(
                            entity_id=entity_id,
                            end_date=as_of_date
                        )
                    else:
                        # 备用方案：使用model
                        finance_model = data_mgr.get_model("corporate_finance")
                        if finance_model:
                            finance_data = finance_model.load_by_stock(entity_id, end_date=as_of_date)
                        else:
                            finance_data = {}
                    historical_data["finance"] = finance_data
                except Exception as e:
                    logger.warning(f"加载财务数据失败: {entity_id}, 错误: {e}")
                    historical_data["finance"] = {}
        
        return historical_data
    
    @staticmethod
    def _filter_data_to_date(historical_data: Dict[str, Any], as_of_date: str) -> Dict[str, Any]:
        """
        过滤数据到指定日期（不包含未来数据）
        
        过滤规则：
        - K线数据：只保留 date <= as_of_date 的记录
        - 财务数据：只保留 quarter/date <= as_of_date 的记录
        - 其他时间序列数据：同样过滤
        
        Args:
            historical_data: 全量历史数据
            as_of_date: 截止日期（YYYYMMDD格式）
            
        Returns:
            Dict[str, Any]: 过滤后的数据
        """
        filtered = {}
        
        # 过滤K线数据
        if "klines" in historical_data:
            filtered["klines"] = {}
            for term, klines in historical_data["klines"].items():
                # 只保留date <= as_of_date的记录
                filtered["klines"][term] = [
                    k for k in klines
                    if k.get("date", "") <= as_of_date
                ]
        
        # 过滤财务数据
        if "finance" in historical_data:
            finance_data = historical_data["finance"]
            if isinstance(finance_data, list):
                # 如果是列表，过滤quarter/date
                filtered["finance"] = [
                    f for f in finance_data
                    if (f.get("quarter", "") <= as_of_date or f.get("date", "") <= as_of_date)
                ]
            elif isinstance(finance_data, dict):
                # 如果是字典，递归过滤
                filtered["finance"] = {
                    k: v for k, v in finance_data.items()
                    if (k <= as_of_date if isinstance(k, str) else True)
                }
            else:
                filtered["finance"] = finance_data
        
        # 其他数据源（如果有）也需要过滤
        for key, value in historical_data.items():
            if key not in ["klines", "finance"]:
                # 对于其他数据源，暂时直接传递（可以根据需要添加过滤逻辑）
                filtered[key] = value
        
        return filtered
    
    @staticmethod
    def _create_calculator_instance_in_process(
        calculator_class,
        settings_path: str,
        data_mgr,
        tag_service
    ):
        """
        在子进程中创建calculator实例（静态方法）
        
        Args:
            calculator_class: Calculator类
            settings_path: Settings文件路径
            data_mgr: DataManager实例
            tag_service: TagService实例
            
        Returns:
            BaseTagCalculator: Calculator实例
        """
        return calculator_class(
            settings_path=settings_path,
            data_mgr=data_mgr,
            tag_service=tag_service
        )
    
    @staticmethod
    def _batch_save_tag_values(results: List[Dict[str, Any]], tag_service):
        """
        批量保存tag值（静态方法）
        
        Args:
            results: Tag值列表
            tag_service: TagService实例
        """
        # 如果tag_service有batch_save_tag_values方法，使用它
        if hasattr(tag_service, "batch_save_tag_values"):
            tag_service.batch_save_tag_values(results)
        else:
            # 否则使用TagValueModel的batch_save_tag_values
            from app.data_manager.base_tables.tag_value.model import TagValueModel
            tag_value_model = TagValueModel()
            
            # 转换格式（tag_definition_id -> tag_id，兼容TagValueModel）
            tag_values = []
            for result in results:
                tag_values.append({
                    'entity_type': result.get('entity_type', 'stock'),
                    'entity_id': result['entity_id'],
                    'tag_id': result['tag_definition_id'],  # TagValueModel使用tag_id
                    'as_of_date': result['as_of_date'],
                    'start_date': result.get('start_date'),
                    'end_date': result.get('end_date'),
                    'value': result['value'],
                })
            
            tag_value_model.batch_save_tag_values(tag_values)
    
    @staticmethod
    def _get_trading_dates_static(start_date: str, end_date: str, data_mgr) -> List[str]:
        """
        获取交易日列表（静态方法，用于子进程）
        
        Args:
            start_date: 起始日期（YYYYMMDD 格式）
            end_date: 结束日期（YYYYMMDD 格式）
            data_mgr: DataManager实例
            
        Returns:
            List[str]: 交易日列表（YYYYMMDD 格式）
        """
        if data_mgr and hasattr(data_mgr, "get_trading_dates"):
            return data_mgr.get_trading_dates(start_date, end_date)
        return []
    
    def cleanup_legacy_versions(self, scenario_name: str, keep_n: int = 3):
        """
        清理旧的 legacy versions
        
        如果 legacy version 数量 >= keep_n，删除最老的
        
        Args:
            scenario_name: Scenario 名称
            keep_n: 最大保留的 legacy version 数量（默认 3，可配置）
        """
        if not self.tag_service:
            raise ValueError("TagService 未初始化，无法清理旧版本")
        
        # 1. 查询所有 legacy scenarios
        all_scenarios = self.tag_service.list_scenarios(
            scenario_name=scenario_name,
            include_legacy=True
        )
        legacy_scenarios = [s for s in all_scenarios if s.get("is_legacy", 0) == 1]
        legacy_scenarios.sort(key=lambda x: x.get("created_at", ""))
        
        # 2. 如果数量 >= keep_n，删除最老的
        if len(legacy_scenarios) >= keep_n:
            delete_count = len(legacy_scenarios) - keep_n + 1
            for i in range(delete_count):
                scenario_to_delete = legacy_scenarios[i]
                self.tag_service.delete_scenario(scenario_to_delete["id"], cascade=True)
                logger.info(f"已删除旧的 legacy scenario: {scenario_name}@{scenario_to_delete['version']}")
    
    # ========================================================================
    # 5. 辅助方法（需要实现）
    # ========================================================================
    
    def _get_max_as_of_date(self, tag_definitions: List[Dict[str, Any]]) -> Optional[str]:
        """
        获取 tag definitions 的最大 as_of_date
        
        Args:
            tag_definitions: Tag Definition 列表
            
        Returns:
            Optional[str]: 最大 as_of_date（YYYYMMDD 格式），如果没有数据则返回 None
        """
        if not tag_definitions:
            return None
        
        max_dates = []
        for tag_def in tag_definitions:
            # 查询该 tag_definition 的最大 as_of_date
            # 这里需要通过 tag_service 查询，或者直接查询数据库
            # 暂时返回 None，需要实现具体的查询逻辑
            pass
        
        if max_dates:
            return max(max_dates)
        return None
    
    def _get_next_trading_date(self, date: str) -> str:
        """
        获取下一个交易日
        
        Args:
            date: 当前日期（YYYYMMDD 格式）
            
        Returns:
            str: 下一个交易日（YYYYMMDD 格式）
        """
        # 从 DataManager 或交易日历获取下一个交易日
        # 暂时返回原日期，需要实现具体的逻辑
        return date
    
    def _get_latest_trading_date(self) -> str:
        """
        获取最新交易日
        
        Returns:
            str: 最新交易日（YYYYMMDD 格式）
        """
        # 从 DataManager 获取最新交易日
        if self.data_mgr and hasattr(self.data_mgr, "get_latest_completed_trading_date"):
            return self.data_mgr.get_latest_completed_trading_date()
        return ""
    
    def _get_default_start_date(self) -> str:
        """
        获取默认起始日期
        
        Returns:
            str: 默认起始日期（YYYYMMDD 格式）
        """
        # 返回一个合理的默认起始日期
        # 例如：一年前或系统配置的默认值
        return ""
    
    def _get_entity_list(self) -> List[str]:
        """
        获取实体列表（如股票列表）
        
        Returns:
            List[str]: 实体ID列表
        """
        # 从 DataManager 获取实体列表
        if self.data_mgr and hasattr(self.data_mgr, "get_stock_list"):
            return self.data_mgr.get_stock_list()
        return []
    
    def _get_trading_dates(self, start_date: str, end_date: str) -> List[str]:
        """
        获取交易日列表
        
        Args:
            start_date: 起始日期（YYYYMMDD 格式）
            end_date: 结束日期（YYYYMMDD 格式）
            
        Returns:
            List[str]: 交易日列表（YYYYMMDD 格式）
        """
        # 从 DataManager 或交易日历获取交易日列表
        if self.data_mgr and hasattr(self.data_mgr, "get_trading_dates"):
            return self.data_mgr.get_trading_dates(start_date, end_date)
        return []
    
    # ========================================================================
    # 6. 其他钩子函数（可选实现）
    # ========================================================================
    
    def on_init(self):
        """
        初始化钩子（可选实现）
        
        在 Calculator 初始化后调用，用于：
        - 初始化缓存
        - 预加载数据
        - 其他初始化操作
        """
        pass
    
    def on_tag_created(self, tag_entity: Any, entity_id: str, as_of_date: str):
        """
        Tag 创建后钩子（可选实现）
        
        在 calculate_tag 返回结果并保存后调用，用于：
        - 记录日志
        - 更新缓存
        - 触发其他操作
        """
        pass
    
    def on_calculate_error(self, entity_id: str, as_of_date: str, error: Exception):
        """
        计算错误钩子（可选实现）
        
        在 calculate_tag 抛出异常时调用，用于：
        - 记录错误日志
        - 发送告警
        - 其他错误处理
        """
        # 默认实现：记录错误
        logger.error(
            f"计算 tag 失败: entity_id={entity_id}, as_of_date={as_of_date}, error={error}",
            exc_info=True
        )
    
    def should_continue_on_error(self) -> bool:
        """
        错误时是否继续（可选实现）
        
        返回 True 表示遇到错误时继续计算下一个时间点
        返回 False 表示遇到错误时中断计算
        
        默认：True（继续）
        """
        return True
    
    def on_finish(self, entity_id: str, tag_count: int):
        """
        完成钩子（可选实现）
        
        在单个实体计算完成后调用，用于：
        - 记录统计信息
        - 清理资源
        - 其他收尾操作
        """
        pass
