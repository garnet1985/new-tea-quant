"""
Settings 验证器

提供静态方法用于验证 Tag Calculator 的 settings 配置。
"""
from typing import Dict, Any
from app.tag.core.enums import KlineTerm, UpdateMode, VersionChangeAction


class SettingsValidator:
    """Settings 配置验证器（静态方法）"""
    
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
        
        # 验证 on_version_change
        scenario = settings["scenario"]
        if "on_version_change" in scenario:
            on_version_change = scenario["on_version_change"]
            valid_actions = [action.value for action in VersionChangeAction]
            if on_version_change not in valid_actions:
                raise ValueError(
                    f"scenario.on_version_change 必须是 {valid_actions} 之一（使用 VersionChangeAction 枚举），"
                    f"当前值: {on_version_change}"
                )
    
    @staticmethod
    def validate_all(settings: Dict[str, Any]):
        """
        验证所有配置（完整验证流程）
        
        Args:
            settings: settings 字典
            
        Raises:
            ValueError: 验证失败
        """
        SettingsValidator.validate_scenario_fields(settings)
        SettingsValidator.validate_calculator_fields(settings)
        SettingsValidator.validate_tags_fields(settings)
        SettingsValidator.validate_enums(settings)
