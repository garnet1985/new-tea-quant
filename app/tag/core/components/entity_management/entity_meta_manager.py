"""
Entity Meta Manager - Scenario 和 Tag 元信息管理器

职责：
1. 确保 scenario 存在（如果不存在则创建）
2. 确保 tag definitions 存在（如果不存在则创建）
3. 处理版本变更
4. 确定计算日期范围
5. 提供统一的元信息管理接口
"""
from typing import Dict, Any, List, Optional, Tuple
import logging
from app.tag.core.enums import UpdateMode, VersionChangeAction
from app.tag.core.config import ALLOW_VERSION_ROLLBACK

logger = logging.getLogger(__name__)


class EntityMetaManager:
    """
    Entity Meta Manager - Scenario 和 Tag 元信息管理器
    
    职责：
    1. 确保 scenario 存在（如果不存在则创建）
    2. 确保 tag definitions 存在（如果不存在则创建）
    3. 提供统一的元信息管理接口
    
    所有方法都是静态方法，tag_data_service 作为参数传入
    """
    
    @staticmethod
    def ensure_metadata(
        tag_data_service,
        scenario_setting: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]], str, str, str]:
        """
        确保元信息存在（scenario 和 tag definitions），并处理版本变更和日期范围
        
        职责：
        1. 处理版本变更（handle_version_change）
        2. 确保 scenario 存在
        3. 确保 tag definitions 存在
        4. 确定计算日期范围
        5. 返回所有需要的信息
        
        Args:
            tag_data_service: TagDataService 实例
            scenario_setting: Scenario settings 字典，包含：
                - "scenario_name": str
                - "settings": Dict[str, Any]
        
        Returns:
            Tuple[Dict[str, Any], List[Dict[str, Any]], str, str, str]: 
            (scenario, tag_definitions, version_action, start_date, end_date)
        """
        # 1. 处理版本变更（可能创建或更新 scenario）
        version_action = EntityMetaManager.handle_version_change(tag_data_service, scenario_setting)
        
        # 2. 确保 scenario 存在（如果版本变更中已创建，这里会直接返回）
        scenario = EntityMetaManager.ensure_scenario(tag_data_service, scenario_setting)
        
        # 3. 确保 tag definitions 存在
        tag_defs = EntityMetaManager.ensure_tags(tag_data_service, scenario, scenario_setting)
        
        # 4. 确定计算日期范围
        start_date, end_date = EntityMetaManager.determine_date_range(
            tag_data_service, scenario_setting, version_action, tag_defs
        )
        
        return scenario, tag_defs, version_action, start_date, end_date
    
    @staticmethod
    def ensure_scenario(tag_data_service, scenario_setting: Dict[str, Any]) -> Dict[str, Any]:
        """
        确保 scenario 存在（如果不存在则创建）
        
        职责：
        1. 查询数据库中该 scenario name 的所有版本
        2. 查找 settings.version 是否已存在
        3. 如果已存在，返回该 scenario
        4. 如果不存在，创建新的 scenario
        
        Args:
            tag_data_service: TagDataService 实例
            scenario_setting: Scenario settings 字典
        
        Returns:
            Dict[str, Any]: Scenario 记录
        """
        if not tag_data_service:
            raise ValueError("TagDataService 未初始化，无法确保 scenario 存在")
        
        settings = scenario_setting["settings"]
        scenario_name = scenario_setting["scenario_name"]
        scenario_version = settings["scenario"]["version"]
        
        # 1. 查询数据库中该 scenario name 的所有版本
        existing_scenarios = tag_data_service.list_scenarios(
            scenario_name=scenario_name
        )
        
        # 2. 查找 settings.version 是否已存在
        target_scenario = None
        for s in existing_scenarios:
            if s.get("version") == scenario_version:
                target_scenario = s
                break
        
        # 3. 如果已存在，返回该 scenario
        if target_scenario:
            return target_scenario
        
        # 4. 如果不存在，创建新的 scenario（通过 TagDataService）
        scenario_id = tag_data_service.create_scenario(
            name=scenario_name,
            version=scenario_version,
            display_name=settings["scenario"].get("display_name", scenario_name),
            description=settings["scenario"].get("description", "")
        )
        
        # 5. 获取新创建的 scenario
        target_scenario = tag_data_service.get_scenario(scenario_name, scenario_version)
        
        if not target_scenario:
            raise ValueError(
                f"创建 scenario 失败: name={scenario_name}, version={scenario_version}"
            )
        
        return target_scenario
    
    @staticmethod
    def ensure_tags(
        tag_data_service,
        scenario: Dict[str, Any], 
        scenario_setting: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        确保 tag definitions 存在（如果不存在则创建）
        
        职责：
        1. 查询该 scenario 下的所有 tag definitions
        2. 对每个 settings.tags 中的 tag：
           a. 检查是否已存在
           b. 如果不存在，创建新的 tag definition
        3. 返回所有 tag definitions 列表
        
        Args:
            tag_data_service: TagDataService 实例
            scenario: Scenario 记录
            scenario_setting: Scenario settings 字典
        
        Returns:
            List[Dict[str, Any]]: Tag Definition 列表
        """
        if not tag_data_service:
            raise ValueError("TagDataService 未初始化，无法确保 tags 存在")
        
        scenario_id = scenario["id"]
        scenario_version = scenario_setting["settings"]["scenario"]["version"]
        settings = scenario_setting["settings"]
        
        # 1. 查询该 scenario 下的所有 tag definitions
        existing_tags = tag_data_service.get_tag_definitions(scenario_id=scenario_id)
        existing_tag_names = {tag["name"] for tag in existing_tags}
        
        # 2. 对每个 settings.tags 中的 tag：
        tag_definitions = []
        for tag_config in settings["tags"]:
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
                tag_definition_id = tag_data_service.create_tag_definition(
                    scenario_id=scenario_id,
                    scenario_version=scenario_version,
                    name=tag_name,
                    display_name=tag_config["display_name"],
                    description=tag_config.get("description", "")
                )
                
                # 获取新创建的 tag definition
                new_tags = tag_data_service.get_tag_definitions(
                    scenario_id=scenario_id, 
                    include_legacy=False
                )
                for tag in new_tags:
                    if tag["name"] == tag_name:
                        tag_definitions.append(tag)
                        break
        
        # 3. 返回 tag definitions 列表
        return tag_definitions
    
    @staticmethod
    def handle_version_change(tag_data_service, scenario_setting: Dict[str, Any]) -> str:
        """
        处理版本变更
        
        职责：
        1. 检查版本是否已存在
        2. 根据版本状态和配置决定版本变更动作
        3. 执行相应的版本变更操作（创建、更新、回退等）
        
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
        
        Args:
            tag_data_service: TagDataService 实例
            scenario_setting: Scenario settings 字典
        
        Returns:
            str: VersionAction ("NO_CHANGE", "ROLLBACK", "NEW_SCENARIO", "REFRESH_SCENARIO")
        """
        if not tag_data_service:
            raise ValueError("TagDataService 未初始化，无法处理版本变更")
        
        settings = scenario_setting["settings"]
        scenario_name = scenario_setting["scenario_name"]
        scenario_version = settings["scenario"]["version"]
        
        # 1. 查询数据库中该 scenario name 的所有版本
        db_scenarios = tag_data_service.list_scenarios(
            scenario_name=scenario_name
        )
        
        # 2. 查找 settings.version 是否在数据库中已存在
        existing_scenario = None
        for s in db_scenarios:
            if s.get("version") == scenario_version:
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
                    f"scenario={scenario_name}, version={scenario_version}. "
                    "Version rollback may cause data inconsistency. "
                    "Only rollback version if worker logic is also rolled back. "
                    "To allow version rollback, set ALLOW_VERSION_ROLLBACK=True in app/tag/core/config.py"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # ALLOW_VERSION_ROLLBACK = True
            warning_msg = (
                f"Version rollback detected: "
                f"scenario={scenario_name}, version={scenario_version}. "
                "WARNING: Version rollback may cause data inconsistency. "
                "Only rollback version if worker logic is also rolled back. "
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
                tag_data_service.mark_scenario_as_legacy(active_scenario["id"])
            
            # 把当前版本（existing_scenario）设置为 legacy=0（active）
            tag_data_service.update_scenario(
                existing_scenario["id"],
                is_legacy=0
            )
            
            # 注意：不删除旧的 tag definitions 和 tag values
            # 确保 tag definitions 存在（调用 ensure_tags，如果不存在则创建）
            scenario = tag_data_service.get_scenario(scenario_name, scenario_version)
            EntityMetaManager.ensure_tags(tag_data_service, scenario, scenario_setting)
            
            return "ROLLBACK"
        
        # 5. 如果不存在：
        # 读取 on_version_change 配置
        on_version_change = settings["scenario"].get(
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
                tag_data_service.mark_scenario_as_legacy(active_scenario["id"])
            
            # 创建新 scenario（ensure_scenario 会处理）
            # 清理旧版本
            EntityMetaManager.cleanup_legacy_versions(tag_data_service, scenario_name, keep_n=3)
            
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
                tag_data_service.update_scenario(
                    active_scenario["id"],
                    display_name=settings["scenario"].get("display_name", scenario_name),
                    description=settings["scenario"].get("description", "")
                )
                # 删除旧的 tag definitions 和 tag values
                tag_data_service.delete_tag_definitions_by_scenario(active_scenario["id"])
                tag_data_service.delete_tag_values_by_scenario(active_scenario["id"])
            # 如果不存在 active 版本，ensure_scenario 会创建新 scenario
            
            # 创建新的 tag definitions（ensure_tags 会处理）
            
            return "REFRESH_SCENARIO"
        
        else:
            raise ValueError(f"未知的 on_version_change 值: {on_version_change}")
    
    @staticmethod
    def determine_date_range(
        tag_data_service,
        scenario_setting: Dict[str, Any],
        version_action: str,
        tag_defs: List[Dict[str, Any]]
    ) -> Tuple[str, str]:
        """
        确定计算日期范围
        
        职责：
        1. 根据 version_action 和 update_mode 确定日期范围
        2. 返回 start_date 和 end_date
        
        Args:
            tag_data_service: TagDataService 实例
            scenario_setting: Scenario settings 字典
            version_action: VersionAction ("NO_CHANGE", "ROLLBACK", "NEW_SCENARIO", "REFRESH_SCENARIO")
            tag_defs: Tag Definition 列表
        
        Returns:
            Tuple[str, str]: (start_date, end_date)
        """
        settings = scenario_setting["settings"]
        update_mode = settings["calculator"]["performance"].get(
            "update_mode",
            UpdateMode.INCREMENTAL.value
        )
        
        if version_action == "NO_CHANGE":
            # 按 update_mode 计算
            if update_mode == UpdateMode.INCREMENTAL.value:
                # 从上次计算的最大 as_of_date 继续
                start_date = EntityMetaManager._get_max_as_of_date(tag_data_service, tag_defs)
                if start_date:
                    # 获取下一个交易日
                    start_date = EntityMetaManager._get_next_trading_date(start_date)
                else:
                    # 如果没有历史数据，从 start_date 开始
                    start_date = settings["calculator"].get("start_date") or EntityMetaManager._get_default_start_date()
                end_date = settings["calculator"].get("end_date") or EntityMetaManager._get_latest_trading_date()
            elif update_mode == UpdateMode.REFRESH.value:
                # 从 start_date 到 end_date
                start_date = settings["calculator"].get("start_date") or EntityMetaManager._get_default_start_date()
                end_date = settings["calculator"].get("end_date") or EntityMetaManager._get_latest_trading_date()
            else:
                raise ValueError(f"未知的 update_mode: {update_mode}")
        
        elif version_action == "ROLLBACK":
            # 版本回退：按照该版本的 update_mode 继续
            logger.warning(
                f"Version rollback detected: scenario={scenario_setting['scenario_name']}, "
                f"version={settings['scenario']['version']}. "
                f"Continuing with update_mode={update_mode}. "
                f"User is responsible for ensuring algorithm consistency."
            )
            if update_mode == UpdateMode.INCREMENTAL.value:
                # 从上次计算的最大 as_of_date 继续
                start_date = EntityMetaManager._get_max_as_of_date(tag_data_service, tag_defs)
                if start_date:
                    start_date = EntityMetaManager._get_next_trading_date(start_date)
                else:
                    start_date = settings["calculator"].get("start_date") or EntityMetaManager._get_default_start_date()
                end_date = settings["calculator"].get("end_date") or EntityMetaManager._get_latest_trading_date()
            elif update_mode == UpdateMode.REFRESH.value:
                start_date = settings["calculator"].get("start_date") or EntityMetaManager._get_default_start_date()
                end_date = settings["calculator"].get("end_date") or EntityMetaManager._get_latest_trading_date()
            else:
                raise ValueError(f"未知的 update_mode: {update_mode}")
        
        elif version_action in ["NEW_SCENARIO", "REFRESH_SCENARIO"]:
            # 新 scenario 或刷新：从 start_date 到 end_date
            start_date = settings["calculator"].get("start_date") or EntityMetaManager._get_default_start_date()
            end_date = settings["calculator"].get("end_date") or EntityMetaManager._get_latest_trading_date()
        
        else:
            raise ValueError(f"未知的 version_action: {version_action}")
        
        return start_date, end_date
    
    @staticmethod
    def _get_max_as_of_date(tag_data_service, tag_defs: List[Dict[str, Any]]) -> Optional[str]:
        """
        获取 tag definitions 的最大 as_of_date
        
        Args:
            tag_data_service: TagDataService 实例
            tag_defs: Tag Definition 列表
        
        Returns:
            Optional[str]: 最大 as_of_date（YYYYMMDD 格式），如果不存在返回 None
        """
        if not tag_defs:
            return None
        
        # 从 tag_data_service 查询最大 as_of_date
        # 这里需要查询所有 tag_definitions 的最大 as_of_date
        max_date = None
        for tag_def in tag_defs:
            # 这里需要 TagDataService 提供查询最大 as_of_date 的方法
            # 暂时返回 None，后续实现
            pass
        
        return max_date
    
    @staticmethod
    def _get_next_trading_date(date: str) -> str:
        """
        获取下一个交易日
        
        Args:
            date: 当前日期（YYYYMMDD 格式）
        
        Returns:
            str: 下一个交易日（YYYYMMDD 格式）
        """
        # 这里需要从 DataManager 或交易日历获取下一个交易日
        # 暂时返回原日期，后续实现
        return date
    
    @staticmethod
    def _get_default_start_date() -> str:
        """
        获取默认起始日期
        
        Returns:
            str: 默认起始日期（YYYYMMDD 格式）
        """
        # 返回一个默认日期，比如 "20000101"
        return "20000101"
    
    @staticmethod
    def _get_latest_trading_date() -> str:
        """
        获取最新交易日
        
        Returns:
            str: 最新交易日（YYYYMMDD 格式）
        """
        # 这里需要从 DataManager 或交易日历获取最新交易日
        # 暂时返回当前日期，后续实现
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d")
    
    @staticmethod
    def cleanup_legacy_versions(tag_data_service, scenario_name: str, keep_n: int = 3):
        """
        清理旧版本（保留最近的 N 个版本）
        
        职责：
        1. 查询所有 legacy scenarios
        2. 如果数量 >= keep_n，删除最老的版本
        
        Args:
            tag_data_service: TagDataService 实例
            scenario_name: Scenario 名称
            keep_n: 保留的版本数量（默认3个）
        """
        if not tag_data_service:
            raise ValueError("TagDataService 未初始化，无法清理旧版本")
        
        # 1. 查询所有 legacy scenarios
        all_scenarios = tag_data_service.list_scenarios(
            scenario_name=scenario_name,
            include_legacy=True
        )
        legacy_scenarios = [s for s in all_scenarios if s.get("is_legacy", 0) == 1]
        legacy_scenarios.sort(key=lambda x: x.get("created_at", ""))
        
        # 2. 如果数量 >= keep_n，删除最老的
        if len(legacy_scenarios) >= keep_n:
            scenarios_to_delete = legacy_scenarios[:-keep_n]
            for scenario_to_delete in scenarios_to_delete:
                tag_data_service.delete_scenario(scenario_to_delete["id"], cascade=True)
                logger.info(
                    f"已删除旧版本 scenario: {scenario_name}, version={scenario_to_delete.get('version')}"
                )
