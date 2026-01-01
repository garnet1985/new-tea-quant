"""
Tag Meta Manager - Scenario 和 Tag 元信息管理器

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
from app.tag.core.models.scenario_model import ScenarioModel
from app.tag.core.models.tag_model import TagModel

logger = logging.getLogger(__name__)


class TagMetaManager:
    """
    Tag Meta Manager - Scenario 和 Tag 元信息管理器
    
    职责：
    1. 确保 scenario 存在（如果不存在则创建）
    2. 确保 tag definitions 存在（如果不存在则创建）
    3. 处理版本变更
    4. 确定计算日期范围
    5. 提供统一的元信息管理接口
    
    实例类，可以缓存 DataManager 和 TagDataService 以便复用
    """

    def __init__(self):
        self.data_mgr = DataManager()
        self.tag_data_service = self.data_mgr.get_tag_service()


    def ensure_metadata(self, scenario_setting: Dict[str, Any]) -> Tuple[ScenarioModel, List[TagModel], str, str, str]:
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
                - "scenario_config": ScenarioModel（不完整的 Model，从 settings 创建）
                - "tags_config": List[TagModel]（不完整的 Model，从 settings 创建）
                - "settings": Dict[str, Any]（原始 settings，用于子进程）
                - "worker_class": type[BaseTagWorker]
        
        Returns:
            Tuple[ScenarioModel, List[TagModel], str, str, str]: 
            (scenario, tag_definitions, version_action, start_date, end_date)
            注意：返回的 Model 都是完整的（所有字段都有值）
        """
        # 从 scenario_setting 中提取 Model（不完整的配置 Model）
        scenario_config = scenario_setting["scenario_config"]
        tags_config = scenario_setting["tags_config"]

        # 先检测版本变更（在确保 scenario 存在之前）
        version_action = self._detect_version_change(scenario_config, scenario_setting)
        
        # 根据版本变更动作处理 scenario（返回完整的 Model）
        scenario = self._ensure_scenario(scenario_config, version_action)
        
        # 确保 tag definitions 存在（返回完整的 Model）
        tag_defs = self._ensure_tags(tags_config, scenario)

        # 验证返回的 Model 都是完整的
        if not scenario.is_complete():
            raise ValueError(f"Scenario Model 不完整: {scenario.name}:{scenario.version}")
        for tag_def in tag_defs:
            if not tag_def.is_complete():
                raise ValueError(f"Tag Model 不完整: {tag_def.tag_name}")

        # 确定计算日期范围
        start_date, end_date = self._determine_date_range(
            scenario_setting, version_action, tag_defs
        )

        return scenario, tag_defs, version_action, start_date, end_date

    def _check_meta_field_diff(
        self,
        current_meta: Any,  # 可以是 Dict 或 Model
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
            
            # 获取当前值（支持 Dict 和 Model）
            if isinstance(current_meta, dict):
                current_value = current_meta.get(field_name)
            else:
                # Model 对象，使用 getattr
                current_value = getattr(current_meta, field_name, None)
            
            # 比较并记录差异
            if current_value != new_value:
                update_data[field_name] = new_value
        
        return update_data

    def _detect_version_change(self, scenario_config: ScenarioModel, scenario_setting: Dict[str, Any] = None) -> str:
        """
        检测版本变更动作
        
        逻辑：
        1. 如果 settings.version 在数据库中已存在且 is_legacy=0（active）：
           - version_action = "NO_CHANGE"（版本未变，继续使用）
        2. 如果 settings.version 在数据库中已存在但 is_legacy=1（legacy）：
           - version_action = "ROLLBACK"（版本回退）
        3. 如果 settings.version 在数据库中不存在：
           - 检查是否有其他 active 版本的 scenario
           - 如果有，读取 on_version_change 配置（需要从 settings 中获取）
           - version_action = on_version_change（REFRESH_SCENARIO 或 NEW_SCENARIO）
           - 如果没有，version_action = "NEW_SCENARIO"（首次创建）
        
        Args:
            scenario_config: scenario 配置 Model（不完整的 Model，从 settings 创建）
        
        Returns:
            str: VersionAction ("NO_CHANGE", "ROLLBACK", "NEW_SCENARIO", "REFRESH_SCENARIO")
        """
        scenario_name = scenario_config.name
        scenario_version = scenario_config.version
        
        # 1. 查询数据库中该 scenario name 的所有版本
        db_scenarios_dict = self.tag_data_service.list_scenarios(scenario_name=scenario_name)
        db_scenarios = [ScenarioModel.from_dict(s) for s in db_scenarios_dict]
        
        # 2. 查找 settings.version 是否在数据库中已存在
        existing_scenario = None
        for scenario in db_scenarios:
            if scenario.version == scenario_version:
                existing_scenario = scenario
                break
        
        # 3. 如果已存在且 is_legacy=0（active）：
        if existing_scenario and not existing_scenario.is_legacy:
            return VersionAction.NO_CHANGE.value
        
        # 4. 如果已存在但 is_legacy=1（legacy）：
        if existing_scenario and existing_scenario.is_legacy:
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
        for scenario in db_scenarios:
            if not scenario.is_legacy:
                active_scenario = scenario
                break
        
        if active_scenario:
            # 有 active 版本，需要从 settings 中读取 on_version_change 配置
            # 注意：scenario_config 不包含 on_version_change，需要从 scenario_setting 中获取
            # 这里暂时从 scenario_setting 中获取，后续可以优化
            # 为了保持接口简洁，我们可以在 scenario_setting 中传递 on_version_change
            # 或者从 scenario_config 中获取（如果我们在 from_settings_dict 中保存了原始配置）
            # 暂时使用默认值
            on_version_change = VersionChangeAction.REFRESH_SCENARIO.value
            
            # TODO: 从 scenario_setting 中获取 on_version_change 配置
            # 或者扩展 ScenarioModel 来保存 on_version_change
            
            if on_version_change == VersionChangeAction.NEW_SCENARIO.value:
                return VersionAction.NEW_SCENARIO.value
            else:  # REFRESH_SCENARIO
                return VersionAction.REFRESH_SCENARIO.value
        else:
            # 没有 active 版本，这是首次创建
            return VersionAction.NEW_SCENARIO.value

    def _ensure_scenario(self, scenario_config: ScenarioModel, version_action: str) -> ScenarioModel:
        """
        确保 scenario 存在（如果不存在则创建，根据版本变更动作处理）
        
        Args:
            scenario_config: scenario 配置 Model（不完整的 Model，从 settings 创建）
            version_action: 版本变更动作（"NO_CHANGE", "ROLLBACK", "NEW_SCENARIO", "REFRESH_SCENARIO"）
        
        Returns:
            ScenarioModel: Scenario 对象（完整的 Model，所有字段都有值）
        """
        scenario_name = scenario_config.name
        scenario_version = scenario_config.version
        scenario_dict = self.tag_data_service.load_scenario(scenario_name, scenario_version)
        scenario = ScenarioModel.from_dict(scenario_dict) if scenario_dict else None

        if scenario:
            # scenario 存在
            if version_action == VersionAction.ROLLBACK.value:
                # 版本回退：标记旧的 active 为 legacy，设置当前为 active
                # 查找当前的 active 版本（is_legacy=0）
                db_scenarios_dict = self.tag_data_service.list_scenarios(scenario_name=scenario_name)
                db_scenarios = [ScenarioModel.from_dict(s) for s in db_scenarios_dict]
                active_scenario = None
                for s in db_scenarios:
                    if not s.is_legacy and s.version != scenario_version:
                        active_scenario = s
                        break
                
                # 如果存在 active 版本，标记为 legacy
                if active_scenario:
                    self.tag_data_service.mark_scenario_as_legacy(active_scenario.id)
                
                # 把当前版本设置为 active
                updated_dict = self.tag_data_service.update_scenario(
                    scenario.id,
                    is_legacy=0,
                    current_scenario=scenario.to_dict()
                )
                return ScenarioModel.from_dict(updated_dict)
            elif version_action == VersionAction.NO_CHANGE.value:
                # 版本未变，检查并更新非关键字段
                field_configs = [
                    {'field_name': 'display_name', 'default_from': 'name'},
                    {'field_name': 'description', 'default_value': ''}
                ]
                update_data = self._check_meta_field_diff(scenario, scenario_info, field_configs)
                
                # 如果有更新，执行更新
                if update_data:
                    logger.info(
                        f"更新 scenario 的非关键字段: {scenario_name} v{scenario_version}, "
                        f"更新字段: {list(update_data.keys())}"
                    )
                    updated_dict = self.tag_data_service.update_scenario(
                        scenario.id,
                        display_name=update_data.get("display_name"),
                        description=update_data.get("description"),
                        current_scenario=scenario.to_dict()  # 传入当前数据，避免额外查询
                    )
                    return ScenarioModel.from_dict(updated_dict)
                
                return scenario
            else:
                # NEW_SCENARIO 或 REFRESH_SCENARIO：不应该走到这里（scenario 应该不存在）
                logger.warning(
                    f"意外的版本变更动作: scenario={scenario_name}, version={scenario_version}, "
                    f"version_action={version_action}, 但 scenario 已存在"
                )
                return scenario
        else:
            # scenario 不存在，创建新的
            # 如果是 NEW_SCENARIO 或 REFRESH_SCENARIO，需要处理旧的 active scenario
            if version_action in [VersionAction.NEW_SCENARIO.value, VersionAction.REFRESH_SCENARIO.value]:
                # 查找当前的 active 版本（is_legacy=0）
                db_scenarios_dict = self.tag_data_service.list_scenarios(scenario_name=scenario_name)
                db_scenarios = [ScenarioModel.from_dict(s) for s in db_scenarios_dict]
                active_scenario = None
                for s in db_scenarios:
                    if not s.is_legacy:
                        active_scenario = s
                        break
                
                # 如果存在 active 版本，标记为 legacy
                if active_scenario:
                    self.tag_data_service.mark_scenario_as_legacy(active_scenario.id)
                    
                    # 如果是 REFRESH_SCENARIO，删除旧的 tag values
                    if version_action == VersionAction.REFRESH_SCENARIO.value:
                        logger.info(
                            f"REFRESH_SCENARIO: 删除旧的 tag values, "
                            f"scenario_id={active_scenario.id}"
                        )
                        self.tag_data_service.delete_tag_values_by_scenario(active_scenario.id)
            
            # 创建新的 scenario
            created_dict = self.tag_data_service.save_scenario(
                scenario_name, 
                scenario_version,
                display_name=scenario_config.display_name,
                description=scenario_config.description
            )
            return ScenarioModel.from_dict(created_dict)

    def _ensure_tag(self, 
        tag_config: TagModel, 
        scenario: ScenarioModel, 
    ) -> TagModel:
        """
        确保 tag definition 存在（如果不存在则创建，如果存在则更新非关键字段）
        
        Args:
            tag_config: tag 配置 Model（不完整的 Model，从 settings 创建）
            scenario: scenario 对象（完整的 Model）
        
        Returns:
            TagModel: Tag definition 对象（完整的 Model，所有字段都有值）
        """
        tag_name = tag_config.tag_name
        scenario_version = scenario.version
        scenario_id = scenario.id
        tag_dict = self.tag_data_service.load_tag(tag_name, scenario_id, scenario_version)
        tag = TagModel.from_dict(tag_dict) if tag_dict else None
        
        if tag:
            # tag 存在，检查并更新非关键字段
            field_configs = [
                {'field_name': 'display_name', 'default_from': 'name'},
                {'field_name': 'description', 'default_value': ''}
            ]
            # 将 tag_config 转换为字典以便 _check_meta_field_diff 使用
            tag_config_dict = {
                'name': tag_config.tag_name,
                'display_name': tag_config.display_name,
                'description': tag_config.description
            }
            update_data = self._check_meta_field_diff(tag, tag_config_dict, field_configs)
            
            # 如果有更新，执行更新
            if update_data:
                logger.info(
                    f"更新 tag 的非关键字段: {tag_name} (scenario_id={scenario_id}), "
                    f"更新字段: {list(update_data.keys())}"
                )
                updated_dict = self.tag_data_service.update_tag_definition(
                    tag.id,
                    display_name=update_data.get("display_name"),
                    description=update_data.get("description"),
                    current_tag=tag.to_dict()  # 传入当前数据，避免额外查询
                )
                return TagModel.from_dict(updated_dict)
            
            return tag
        else:
            # tag 不存在，创建新的
            created_dict = self.tag_data_service.save_tag(
                tag_name, 
                scenario_id, 
                scenario_version, 
                tag_config.display_name, 
                tag_config.description
            )
            return TagModel.from_dict(created_dict)

    def _ensure_tags(self, 
        tags_config: List[TagModel], 
        scenario: ScenarioModel, 
    ) -> List[TagModel]:
        """
        确保所有 tag definitions 存在（批量优化版本）
        
        优化策略：
        1. 批量加载所有已存在的 tags（1次查询）
        2. 逐个检查并更新/创建（减少查询次数）
        
        Args:
            tags_config: tag 配置 Model 列表（不完整的 Model，从 settings 创建）
            scenario: scenario 对象（完整的 Model）
        
        Returns:
            List[TagModel]: Tag definition 列表（完整的 Model，所有字段都有值）
        """
        scenario_id = scenario.id
        scenario_version = scenario.version
        
        # 优化：批量加载所有已存在的 tags（1次查询）
        existing_tags_dict = self.tag_data_service.get_tag_definitions(
            scenario_id=scenario_id,
            include_legacy=False
        )
        existing_tags = [TagModel.from_dict(t) for t in existing_tags_dict]
        existing_tags_map = {tag.tag_name: tag for tag in existing_tags}
        
        tags_meta = []
        tags_to_create = []
        tags_to_update = []
        
        # 第一遍：检查哪些需要创建，哪些需要更新
        for tag_config in tags_config:
            tag_name = tag_config.tag_name
            existing_tag = existing_tags_map.get(tag_name)
            
            if existing_tag:
                # tag 存在，检查是否需要更新非关键字段
                field_configs = [
                    {'field_name': 'display_name', 'default_from': 'name'},
                    {'field_name': 'description', 'default_value': ''}
                ]
                # 将 tag_config 转换为字典以便 _check_meta_field_diff 使用
                tag_config_dict = {
                    'name': tag_config.tag_name,
                    'display_name': tag_config.display_name,
                    'description': tag_config.description
                }
                update_data = self._check_meta_field_diff(existing_tag, tag_config_dict, field_configs)
                
                if update_data:
                    tags_to_update.append({
                        'tag': existing_tag,
                        'update_data': update_data,
                        'tag_config': tag_config
                    })
                else:
                    tags_meta.append(existing_tag)
            else:
                # tag 不存在，需要创建
                tags_to_create.append(tag_config)
        
        # 批量创建新 tags
        for tag_config in tags_to_create:
            tag_dict = self.tag_data_service.save_tag(
                tag_config.tag_name,
                scenario_id,
                scenario_version,
                tag_config.display_name,
                tag_config.description
            )
            tags_meta.append(TagModel.from_dict(tag_dict))
        
        # 批量更新需要更新的 tags（优化：使用批量更新 SQL）
        if tags_to_update:
            logger.info(
                f"批量更新 {len(tags_to_update)} 个 tag 的非关键字段 (scenario_id={scenario_id})"
            )
            
            # 准备批量更新数据
            batch_updates = []
            for update_item in tags_to_update:
                existing_tag = update_item['tag']
                update_dict = {
                    'tag_definition_id': existing_tag.id,
                    'current_tag': existing_tag.to_dict()  # 传入当前数据，避免额外查询
                }
                # 只添加实际需要更新的字段
                if "display_name" in update_item['update_data']:
                    update_dict['display_name'] = update_item['update_data']['display_name']
                if "description" in update_item['update_data']:
                    update_dict['description'] = update_item['update_data']['description']
                batch_updates.append(update_dict)
            
            # 执行批量更新（1次 SQL 更新）
            updated_tags_dict = self.tag_data_service.batch_update_tag_definitions(batch_updates)
            updated_tags = [TagModel.from_dict(t) for t in updated_tags_dict]
            tags_meta.extend(updated_tags)
        
        return tags_meta

    def _determine_date_range(
        self,
        scenario_setting: Dict[str, Any],
        version_action: str,
        tag_defs: List[TagModel]
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

    def _get_max_as_of_date(self, tag_defs: List[TagModel]) -> Optional[str]:
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
        tag_definition_ids = [tag_def.id for tag_def in tag_defs if tag_def.id]
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