"""
Settings Manager - 统一的 Settings 管理器

职责：
1. 读取和处理 settings（读取文件、应用默认值）
2. 验证 settings（结构和枚举）
3. 提供统一的接口给 TagManager 和 TagWorker 使用
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import importlib.util
import os
from loguru import logger

from app.tag.core.enums import KlineTerm, UpdateMode
from utils.file.file_util import FileUtil


class SettingsHelper:
    """
    Settings Helper

    职责：
    1. 读取和处理 settings（读取文件、应用默认值）
    2. 验证 settings（结构和枚举）
    3. 提供统一的验证接口
    """

    # -------------------------------------------------------------------------
    # 读取和处理 settings
    # -------------------------------------------------------------------------

    @staticmethod
    def merge_tag_config(
        tag_config: Dict[str, Any],
        calculator_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        合并 calculator 和 tag 配置
        
        注意：tag 级别不支持 core 和 performance，只在 calculator 级别配置
        
        Args:
            tag_config: tag 配置字典
            calculator_config: calculator 配置字典
        
        Returns:
            Dict[str, Any]: 合并后的配置
        """
        # 复制 calculator 配置
        merged = calculator_config.copy()
        
        # 注意：tag 级别不支持 core 和 performance，直接使用 calculator 的配置
        # core 和 performance 只在 calculator 级别配置，所有 tags 共享
        
        # 添加 tag 元信息
        merged["tag_meta"] = {
            "name": tag_config["name"],
            "display_name": tag_config["display_name"],
            "description": tag_config.get("description", ""),
        }
        
        return merged

    # -------------------------------------------------------------------------
    # 验证 settings（原 SettingsValidator 方法）
    # -------------------------------------------------------------------------

    @staticmethod
    def validate_scenario_fields(settings: Dict[str, Any]):
        """
        验证 scenario 配置字段
        
        Args:
            settings: settings 字典
            
        Raises:
            ValueError: 验证失败
        """
        if "scenario" not in settings:
            raise ValueError("Settings 缺少 'scenario' 字段")
        
        scenario = settings["scenario"]
        if not isinstance(scenario, dict):
            raise ValueError("Settings.scenario 必须是字典类型")
        
        if "name" not in scenario:
            raise ValueError("Settings.scenario 缺少 'name' 字段")
        
        if "version" not in scenario:
            raise ValueError("Settings.scenario 缺少 'version' 字段")

    @staticmethod
    def validate_calculator_fields(settings: Dict[str, Any]):
        """
        验证 calculator 配置字段
        
        Args:
            settings: settings 字典
            
        Raises:
            ValueError: 验证失败
        """
        if "calculator" not in settings:
            raise ValueError("Settings 缺少 'calculator' 字段")
        
        calculator = settings["calculator"]
        if not isinstance(calculator, dict):
            raise ValueError("Settings.calculator 必须是字典类型")
        
        if "base_term" not in calculator:
            raise ValueError("Settings.calculator 缺少 'base_term' 字段")

    @staticmethod
    def validate_tags_fields(settings: Dict[str, Any]):
        """
        验证 tags 配置字段
        
        Args:
            settings: settings 字典
            
        Raises:
            ValueError: 验证失败
        """
        if "tags" not in settings:
            raise ValueError("Settings 缺少 'tags' 字段")
        
        tags = settings["tags"]
        if not isinstance(tags, list):
            raise ValueError("Settings.tags 必须是列表类型")
        
        if len(tags) == 0:
            raise ValueError("Settings.tags 至少需要包含一个 tag")
        
        # 验证每个 tag
        tag_names = set()
        for i, tag in enumerate(tags):
            if not isinstance(tag, dict):
                raise ValueError(f"Settings.tags[{i}] 必须是字典类型")
            
            if "name" not in tag:
                raise ValueError(f"Settings.tags[{i}] 缺少 'name' 字段")
            
            if "display_name" not in tag:
                raise ValueError(f"Settings.tags[{i}] 缺少 'display_name' 字段")
            
            # 检查 tag name 唯一性
            tag_name = tag["name"]
            if tag_name in tag_names:
                raise ValueError(f"Settings.tags 中存在重复的 tag name: {tag_name}")
            tag_names.add(tag_name)

    @staticmethod
    def validate_enums(settings: Dict[str, Any]):
        """
        验证枚举值
        
        Args:
            settings: settings 字典
            
        Raises:
            ValueError: 验证失败
        """
        calculator = settings["calculator"]
        
        # 验证 base_term
        base_term = calculator["base_term"]
        valid_terms = [term.value for term in KlineTerm]
        if base_term not in valid_terms:
            raise ValueError(
                f"calculator.base_term 必须是 {valid_terms} 之一（使用 KlineTerm 枚举），"
                f"当前值: {base_term}"
            )
        
        # 验证 required_terms
        required_terms = calculator.get("required_terms", [])
        if required_terms:
            for term in required_terms:
                if term not in valid_terms:
                    raise ValueError(
                        f"calculator.required_terms 中的值必须是 {valid_terms} 之一（使用 KlineTerm 枚举），"
                        f"当前值: {term}"
                    )
        
        # 验证 update_mode
        perf = calculator.get("performance", {})
        if "update_mode" in perf:
            update_mode = perf["update_mode"]
            valid_modes = [mode.value for mode in UpdateMode]
            if update_mode not in valid_modes:
                raise ValueError(
                    f"calculator.performance.update_mode 必须是 {valid_modes} 之一（使用 UpdateMode 枚举），"
                    f"当前值: {update_mode}"
                )
        
        # on_version_change 已废弃，不再验证
        # scenario = settings["scenario"]
        # if "on_version_change" in scenario:
        #     on_version_change = scenario["on_version_change"]
        #     valid_actions = [action.value for action in VersionChangeAction]
        #     if on_version_change not in valid_actions:
        #         raise ValueError(...)

    # @staticmethod
    # def validate_settings(settings: Dict[str, Any]) -> None:
    #     """
    #     验证 settings 是否有效（抛出异常）
        
    #     完整验证流程：
    #     1. 验证 scenario 字段
    #     2. 验证 calculator 字段
    #     3. 验证 tags 字段
    #     4. 验证枚举值

    #     Args:
    #         settings: settings 字典

    #     Raises:
    #         ValueError: 如果验证失败
    #     """
    #     SettingsManager.validate_scenario_fields(settings)
    #     SettingsManager.validate_calculator_fields(settings)
    #     SettingsManager.validate_tags_fields(settings)
    #     SettingsManager.validate_enums(settings)

    # @staticmethod
    # def is_valid_scenario_setting(scenario_setting: Dict[str, Any]) -> bool:
    #     """
    #     验证 scenario_setting 是否有效（返回 bool）

    #     职责：
    #     1. 验证 settings 基本结构
    #     2. 验证枚举值

    #     Args:
    #         scenario_setting: Scenario settings 字典，包含：
    #             - "settings": Dict[str, Any]

    #     Returns:
    #         bool: 如果有效返回 True，否则返回 False
    #     """
    #     if not isinstance(scenario_setting, dict):
    #         return False

    #     settings = scenario_setting.get("settings")
    #     if not settings:
    #         logger.warning(f"settings must be wrapped by a variable called 'settings'.")
    #         return False

    #     try:
    #         SettingsManager.validate_settings(settings)
    #         return True
    #     except (ValueError, KeyError, TypeError):
    #         return False

    # # -------------------------------------------------------------------------
    # # 提取和处理配置
    # # -------------------------------------------------------------------------

    # @staticmethod
    # def extract_calculator_config(settings: Dict[str, Any]) -> Dict[str, Any]:
    #     """
    #     提取 calculator 配置到字典（方便访问）
        
    #     Args:
    #         settings: settings 字典
            
    #     Returns:
    #         Dict[str, Any]: 提取的配置字典
    #             - scenario_name: str
    #             - base_term: str
    #             - required_terms: List[str]
    #             - required_data: List[str]
    #             - core: Dict[str, Any]
    #             - performance: Dict[str, Any]
    #     """
    #     scenario = settings["scenario"]
    #     calculator = settings["calculator"]
        
    #     return {
    #         "scenario_name": scenario["name"],
    #         "base_term": calculator["base_term"],
    #         "required_terms": calculator.get("required_terms", []),
    #         "required_data": calculator.get("required_data", []),
    #         "core": calculator.get("core", {}),
    #         "performance": calculator.get("performance", {}),
    #     }

    # @staticmethod
    # def process_tags_config(
    #     tags: List[Dict[str, Any]],
    #     calculator_config: Dict[str, Any],
    # ) -> List[Dict[str, Any]]:
    #     """
    #     处理 tags 配置（合并 calculator 和 tag 配置）
        
    #     Args:
    #         tags: tags 配置列表
    #         calculator_config: calculator 配置字典
        
    #     Returns:
    #         List[Dict[str, Any]]: 处理后的 tags 配置列表
    #     """
    #     processed_tags = []
        
    #     for tag in tags:
    #         # 合并配置
    #         merged_config = SettingsManager.merge_tag_config(tag, calculator_config)
    #         processed_tags.append(merged_config)
        
    #     return processed_tags