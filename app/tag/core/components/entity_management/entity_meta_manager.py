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
from app.data_manager import DataManager
from app.tag.core.enums import UpdateMode, VersionChangeAction, VersionAction
from app.tag.core.config import ALLOW_VERSION_ROLLBACK
from app.conf.conf import data_default_start_date

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

    def __init__(self):
        self.data_mgr = DataManager()
        self.tag_data_service = self.data_mgr.get_tag_service()


    def ensure_metadata(self, scenario_setting: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]], str, str, str]:
        """
        确保元信息存在（scenario 和 tag definitions），并处理版本变更和日期范围
        
        职责：
        1. 处理版本变更（handle_version_change）
        2. 确保 scenario 存在
        3. 确保 tag definitions 存在
        4. 确定计算日期范围
        
        Args:
            scenario_setting: Scenario settings 字典，包含：
                - "scenario_name": str
                - "settings": Dict[str, Any]
                - "worker_class": type[BaseTagWorker]
        
        Returns:
            Tuple[Dict[str, Any], List[Dict[str, Any]], str, str, str]: 
            (scenario, tag_definitions, version_action, start_date, end_date)
        """
        # 从 scenario_setting 中提取 settings
        settings = scenario_setting["settings"]
        scenario_info = settings["scenario"]
        tags_info = settings["tags"]

        # 先检测版本变更（在确保 scenario 存在之前）
        version_action = self._detect_version_change(scenario_info)
        
        # 根据版本变更动作处理 scenario
        scenario_meta = self._ensure_scenario(scenario_info, version_action)
        
        # 确保 tag definitions 存在
        tags_meta = self._ensure_tags(tags_info, scenario_meta)

        # 确定计算日期范围
        start_date, end_date = self._determine_date_range(
            scenario_setting, version_action, tags_meta
        )

        return scenario_meta, tags_meta, version_action, start_date, end_date

    def _check_meta_field_diff(
        self,
        current_meta: Dict[str, Any],
        new_config: Dict[str, Any],
        field_configs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        检查非关键字段的差异，返回需要更新的字段字典
        
        这是一个通用的字段差异检查方法，类似于一个大的 switch 语句，
        便于以后扩展新的非关键字段。
        
        Args:
            current_meta: 当前数据库中的元数据
            new_config: 新的配置数据
            field_configs: 字段配置列表，每个元素包含：
                - 'field_name': str - 数据库字段名（必需）
                - 'config_key': str - 在 new_config 中的键名（可选，默认与 field_name 相同）
                - 'default_value': Any - 默认值（可选）
                - 'default_from': str - 从哪个字段获取默认值（可选，如 'name'）
        
        Returns:
            Dict[str, Any]: 需要更新的字段字典，key 为字段名，value 为新值
            如果为空则表示无需更新
        
        Example:
            field_configs = [
                {'field_name': 'display_name', 'default_from': 'name'},
                {'field_name': 'description', 'default_value': ''}
            ]
            diff = self._check_meta_field_diff(current_meta, new_config, field_configs)
        """
        update_data = {}
        
        for field_config in field_configs:
            field_name = field_config['field_name']
            config_key = field_config.get('config_key', field_name)
            
            # 获取新值
            if 'default_from' in field_config:
                # 从指定字段获取默认值
                default_from_key = field_config['default_from']
                new_value = new_config.get(config_key, new_config.get(default_from_key, ''))
            elif 'default_value' in field_config:
                # 使用指定的默认值
                new_value = new_config.get(config_key, field_config['default_value'])
            else:
                # 没有默认值，直接获取
                new_value = new_config.get(config_key)
            
            # 获取当前值
            current_value = current_meta.get(field_name)
            
            # 比较并记录差异
            if current_value != new_value:
                update_data[field_name] = new_value
        
        return update_data

    def _detect_version_change(self, scenario_info: Dict[str, Any]) -> str:
        """
        检测版本变更动作
        
        逻辑：
        1. 如果 settings.version 在数据库中已存在且 is_legacy=0（active）：
           - version_action = "NO_CHANGE"（版本未变，继续使用）
        2. 如果 settings.version 在数据库中已存在但 is_legacy=1（legacy）：
           - version_action = "ROLLBACK"（版本回退）
        3. 如果 settings.version 在数据库中不存在：
           - 检查是否有其他 active 版本的 scenario
           - 如果有，读取 on_version_change 配置
           - version_action = on_version_change（REFRESH_SCENARIO 或 NEW_SCENARIO）
           - 如果没有，version_action = "NEW_SCENARIO"（首次创建）
        
        Args:
            scenario_info: scenario 配置字典，包含 name 和 version
        
        Returns:
            str: VersionAction ("NO_CHANGE", "ROLLBACK", "NEW_SCENARIO", "REFRESH_SCENARIO")
        """
        scenario_name = scenario_info["name"]
        scenario_version = scenario_info["version"]
        
        # 1. 查询数据库中该 scenario name 的所有版本
        db_scenarios = self.tag_data_service.list_scenarios(scenario_name=scenario_name)
        
        # 2. 查找 settings.version 是否在数据库中已存在
        existing_scenario = None
        for s in db_scenarios:
            if s.get("version") == scenario_version:
                existing_scenario = s
                break
        
        # 3. 如果已存在且 is_legacy=0（active）：
        if existing_scenario and existing_scenario.get("is_legacy", 0) == 0:
            return VersionAction.NO_CHANGE.value
        
        # 4. 如果已存在但 is_legacy=1（legacy）：
        if existing_scenario and existing_scenario.get("is_legacy", 0) == 1:
            # 这是用户把 version 改回到以前存在过的版本（版本回退）
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
            
            logger.warning(
                f"版本回退检测: scenario={scenario_name}, version={scenario_version}. "
                f"警告：版本回退可能导致数据不一致，请确保计算逻辑也已回退。"
            )
            return VersionAction.ROLLBACK.value
        
        # 5. 如果不存在：检查是否有其他 active 版本的 scenario
        active_scenario = None
        for s in db_scenarios:
            if s.get("is_legacy", 0) == 0:
                active_scenario = s
                break
        
        if active_scenario:
            # 有 active 版本，读取 on_version_change 配置
            on_version_change = scenario_info.get(
                "on_version_change",
                VersionChangeAction.REFRESH_SCENARIO.value
            )
            
            if on_version_change == VersionChangeAction.NEW_SCENARIO.value:
                return VersionAction.NEW_SCENARIO.value
            else:  # REFRESH_SCENARIO
                return VersionAction.REFRESH_SCENARIO.value
        else:
            # 没有 active 版本，这是首次创建
            return VersionAction.NEW_SCENARIO.value

    def _ensure_scenario(self, scenario_info: Dict[str, Any], version_action: str) -> Dict[str, Any]:
        """
        确保 scenario 存在（如果不存在则创建，根据版本变更动作处理）
        
        Args:
            scenario_info: scenario 配置字典，包含 name 和 version
            version_action: 版本变更动作（"NO_CHANGE", "ROLLBACK", "NEW_SCENARIO", "REFRESH_SCENARIO"）
        
        Returns:
            Dict[str, Any]: Scenario 记录
        """
        scenario_name = scenario_info["name"]
        scenario_version = scenario_info["version"]
        scenario_meta = self.tag_data_service.load_scenario(scenario_name, scenario_version)

        if scenario_meta:
            # scenario 存在
            if version_action == VersionAction.ROLLBACK.value:
                # 版本回退：标记旧的 active 为 legacy，设置当前为 active
                # 查找当前的 active 版本（is_legacy=0）
                db_scenarios = self.tag_data_service.list_scenarios(scenario_name=scenario_name)
                active_scenario = None
                for s in db_scenarios:
                    if s.get("is_legacy", 0) == 0 and s.get("version") != scenario_version:
                        active_scenario = s
                        break
                
                # 如果存在 active 版本，标记为 legacy
                if active_scenario:
                    self.tag_data_service.mark_scenario_as_legacy(active_scenario["id"])
                
                # 把当前版本设置为 active
                return self.tag_data_service.update_scenario(
                    scenario_meta['id'],
                    is_legacy=0,
                    current_scenario=scenario_meta
                )
            elif version_action == VersionAction.NO_CHANGE.value:
                # 版本未变，检查并更新非关键字段
                field_configs = [
                    {'field_name': 'display_name', 'default_from': 'name'},
                    {'field_name': 'description', 'default_value': ''}
                ]
                update_data = self._check_meta_field_diff(scenario_meta, scenario_info, field_configs)
                
                # 如果有更新，执行更新
                if update_data:
                    logger.info(
                        f"更新 scenario 的非关键字段: {scenario_name} v{scenario_version}, "
                        f"更新字段: {list(update_data.keys())}"
                    )
                    return self.tag_data_service.update_scenario(
                        scenario_meta['id'],
                        display_name=update_data.get("display_name"),
                        description=update_data.get("description"),
                        current_scenario=scenario_meta  # 传入当前数据，避免额外查询
                    )
                
                return scenario_meta
            else:
                # NEW_SCENARIO 或 REFRESH_SCENARIO：不应该走到这里（scenario 应该不存在）
                logger.warning(
                    f"意外的版本变更动作: scenario={scenario_name}, version={scenario_version}, "
                    f"version_action={version_action}, 但 scenario 已存在"
                )
                return scenario_meta
        else:
            # scenario 不存在，创建新的
            # 如果是 NEW_SCENARIO 或 REFRESH_SCENARIO，需要处理旧的 active scenario
            if version_action in [VersionAction.NEW_SCENARIO.value, VersionAction.REFRESH_SCENARIO.value]:
                # 查找当前的 active 版本（is_legacy=0）
                db_scenarios = self.tag_data_service.list_scenarios(scenario_name=scenario_name)
                active_scenario = None
                for s in db_scenarios:
                    if s.get("is_legacy", 0) == 0:
                        active_scenario = s
                        break
                
                # 如果存在 active 版本，标记为 legacy
                if active_scenario:
                    self.tag_data_service.mark_scenario_as_legacy(active_scenario["id"])
                    
                    # 如果是 REFRESH_SCENARIO，删除旧的 tag values
                    if version_action == VersionAction.REFRESH_SCENARIO.value:
                        logger.info(
                            f"REFRESH_SCENARIO: 删除旧的 tag values, "
                            f"scenario_id={active_scenario['id']}"
                        )
                        self.tag_data_service.delete_tag_values_by_scenario(active_scenario["id"])
            
            # 创建新的 scenario
            display_name = scenario_info.get("display_name", scenario_name)
            description = scenario_info.get("description", "")
            return self.tag_data_service.save_scenario(
                scenario_name, 
                scenario_version,
                display_name=display_name,
                description=description
            )

    def _ensure_tag(self, 
        tag_info: Dict[str, Any], 
        scenario_meta: Dict[str, Any], 
    ) -> Dict[str, Any]:
        """
        确保 tag definition 存在（如果不存在则创建，如果存在则更新非关键字段）
        
        Args:
            tag_info: tag 配置字典，包含 name, display_name, description
            scenario_meta: scenario 记录
        
        Returns:
            Dict[str, Any]: Tag definition 记录
        """
        tag_name = tag_info["name"]
        scenario_version = scenario_meta['version']
        scenario_id = scenario_meta['id']
        tag_meta = self.tag_data_service.load_tag(tag_name, scenario_id, scenario_version)
        
        if tag_meta:
            # tag 存在，检查并更新非关键字段
            field_configs = [
                {'field_name': 'display_name', 'default_from': 'name'},
                {'field_name': 'description', 'default_value': ''}
            ]
            update_data = self._check_meta_field_diff(tag_meta, tag_info, field_configs)
            
            # 如果有更新，执行更新
            if update_data:
                logger.info(
                    f"更新 tag 的非关键字段: {tag_name} (scenario_id={scenario_id}), "
                    f"更新字段: {list(update_data.keys())}"
                )
                return self.tag_data_service.update_tag_definition(
                    tag_meta['id'],
                    display_name=update_data.get("display_name"),
                    description=update_data.get("description"),
                    current_tag=tag_meta  # 传入当前数据，避免额外查询
                )
            
            return tag_meta
        else:
            # tag 不存在，创建新的
            return self.tag_data_service.save_tag(
                tag_name, 
                scenario_id, 
                scenario_version, 
                tag_info['display_name'], 
                tag_info.get('description', '')
            )

    def _ensure_tags(self, 
        tags_info: List[Dict[str, Any]], 
        scenario_meta: Dict[str, Any], 
    ) -> List[Dict[str, Any]]:
        """
        确保所有 tag definitions 存在（批量优化版本）
        
        优化策略：
        1. 批量加载所有已存在的 tags（1次查询）
        2. 逐个检查并更新/创建（减少查询次数）
        
        Args:
            tags_info: tag 配置列表
            scenario_meta: scenario 记录
        
        Returns:
            List[Dict[str, Any]]: Tag definition 列表
        """
        scenario_id = scenario_meta['id']
        scenario_version = scenario_meta['version']
        
        # 优化：批量加载所有已存在的 tags（1次查询）
        existing_tags = self.tag_data_service.get_tag_definitions(
            scenario_id=scenario_id,
            include_legacy=False
        )
        existing_tags_map = {tag['name']: tag for tag in existing_tags}
        
        tags_meta = []
        tags_to_create = []
        tags_to_update = []
        
        # 第一遍：检查哪些需要创建，哪些需要更新
        for tag_info in tags_info:
            tag_name = tag_info["name"]
            existing_tag = existing_tags_map.get(tag_name)
            
            if existing_tag:
                # tag 存在，检查是否需要更新非关键字段
                field_configs = [
                    {'field_name': 'display_name', 'default_from': 'name'},
                    {'field_name': 'description', 'default_value': ''}
                ]
                update_data = self._check_meta_field_diff(existing_tag, tag_info, field_configs)
                
                if update_data:
                    tags_to_update.append({
                        'tag_definition_id': existing_tag['id'],
                        'update_data': update_data,
                        'tag_info': tag_info
                    })
                else:
                    tags_meta.append(existing_tag)
            else:
                # tag 不存在，需要创建
                tags_to_create.append(tag_info)
        
        # 批量创建新 tags
        for tag_info in tags_to_create:
            tag_meta = self.tag_data_service.save_tag(
                tag_info['name'],
                scenario_id,
                scenario_version,
                tag_info['display_name'],
                tag_info.get('description', '')
            )
            tags_meta.append(tag_meta)
        
        # 批量更新需要更新的 tags（优化：使用批量更新 SQL）
        if tags_to_update:
            logger.info(
                f"批量更新 {len(tags_to_update)} 个 tag 的非关键字段 (scenario_id={scenario_id})"
            )
            
            # 准备批量更新数据
            batch_updates = []
            for update_item in tags_to_update:
                existing_tag = existing_tags_map.get(update_item['tag_info']['name'])
                update_dict = {
                    'tag_definition_id': update_item['tag_definition_id'],
                    'current_tag': existing_tag  # 传入当前数据，避免额外查询
                }
                # 只添加实际需要更新的字段
                if "display_name" in update_item['update_data']:
                    update_dict['display_name'] = update_item['update_data']['display_name']
                if "description" in update_item['update_data']:
                    update_dict['description'] = update_item['update_data']['description']
                batch_updates.append(update_dict)
            
            # 执行批量更新（1次 SQL 更新）
            updated_tags = self.tag_data_service.batch_update_tag_definitions(batch_updates)
            tags_meta.extend(updated_tags)
        
        return tags_meta

    def _determine_date_range(
        self,
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
            scenario_setting: Scenario settings 字典
            version_action: VersionAction ("NO_CHANGE", "ROLLBACK", "NEW_SCENARIO", "REFRESH_SCENARIO")
            tag_defs: Tag Definition 列表
        
        Returns:
            Tuple[str, str]: (start_date, end_date) - 日期格式 YYYYMMDD
        """
        settings = scenario_setting["settings"]
        calculator = settings.get("calculator", {})
        performance = calculator.get("performance", {})
        update_mode = performance.get("update_mode", UpdateMode.INCREMENTAL.value)
        
        # 获取用户配置的日期（如果有）
        user_start_date = calculator.get("start_date", "")
        user_end_date = calculator.get("end_date", "")
        
        # 获取默认 end_date（最新已完成交易日）
        default_end_date = self.data_mgr.get_latest_completed_trading_date()
        
        # 根据 version_action 和 update_mode 确定日期范围
        if version_action in [VersionAction.NEW_SCENARIO.value, VersionAction.REFRESH_SCENARIO.value]:
            # 新 scenario 或刷新：从用户配置的 start_date 到 end_date（全量计算）
            start_date = user_start_date if user_start_date else data_default_start_date
            end_date = user_end_date if user_end_date else default_end_date
            
        elif version_action == VersionAction.ROLLBACK.value:
            # 版本回退：按照该版本的 update_mode 继续
            if update_mode == UpdateMode.INCREMENTAL.value:
                # 增量模式：从上次计算的最大 as_of_date 继续
                max_as_of_date = self._get_max_as_of_date(tag_defs)
                if max_as_of_date:
                    # 获取下一个交易日
                    start_date = self._get_next_trading_date(max_as_of_date)
                else:
                    # 如果没有历史数据，从用户配置的 start_date 开始
                    start_date = user_start_date if user_start_date else data_default_start_date
                end_date = user_end_date if user_end_date else default_end_date
            else:  # REFRESH
                # 刷新模式：使用用户配置的起点和终点
                start_date = user_start_date if user_start_date else data_default_start_date
                end_date = user_end_date if user_end_date else default_end_date
                
        else:  # NO_CHANGE
            # 版本未变：按 update_mode 计算
            if update_mode == UpdateMode.INCREMENTAL.value:
                # 增量模式：从上次计算的最大 as_of_date 继续
                max_as_of_date = self._get_max_as_of_date(tag_defs)
                if max_as_of_date:
                    # 获取下一个交易日
                    start_date = self._get_next_trading_date(max_as_of_date)
                else:
                    # 如果没有历史数据，从用户配置的 start_date 开始
                    start_date = user_start_date if user_start_date else data_default_start_date
                end_date = user_end_date if user_end_date else default_end_date
            else:  # REFRESH
                # 刷新模式：使用用户配置的起点和终点，删除之前的计算结果重新入库
                start_date = user_start_date if user_start_date else data_default_start_date
                end_date = user_end_date if user_end_date else default_end_date
        
        return start_date, end_date

    def _get_max_as_of_date(self, tag_defs: List[Dict[str, Any]]) -> Optional[str]:
        """
        获取 tag definitions 的最大 as_of_date
        
        Args:
            tag_defs: Tag Definition 列表
        
        Returns:
            Optional[str]: 最大 as_of_date（YYYYMMDD 格式），如果没有数据则返回 None
        """
        if not tag_defs:
            return None
        
        # 获取所有 tag_definition_id
        tag_definition_ids = [tag_def.get("id") for tag_def in tag_defs if tag_def.get("id")]
        if not tag_definition_ids:
            return None
        
        # 使用 TagDataService 的 API 查询最大 as_of_date
        return self.tag_data_service.get_max_as_of_date(tag_definition_ids)

    def _get_next_trading_date(self, date: str) -> str:
        """
        获取下一个交易日
        
        Args:
            date: 当前日期（YYYYMMDD 格式）
        
        Returns:
            str: 下一个交易日（YYYYMMDD 格式）
        """
        # 使用 TagDataService 的 API 获取下一个交易日
        return self.tag_data_service.get_next_trading_date(date)