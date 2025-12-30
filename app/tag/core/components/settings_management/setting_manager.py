"""
Settings Manager - 统一的 Settings 管理器

职责：
1. 读取和处理 settings（SettingsProcessor）
2. 验证 settings（SettingsValidator）
3. 提供统一的验证接口给 TagManager 和 TagWorker 使用
"""
from typing import Dict, Any, List

from app.tag.core.components.settings_management.settings_validator import (
    SettingsValidator,
)
from app.tag.core.components.settings_management.settings_processor import (
    SettingsProcessor,
)


class SettingsManager:
    """
    Settings Manager

    职责：
    1. 读取和处理 settings（读取文件、应用默认值）
    2. 验证 settings（结构和枚举）
    3. 提供统一的验证接口
    """

    # -------------------------------------------------------------------------
    # 读取和处理 settings
    # -------------------------------------------------------------------------

    def load_settings_from_file(self, settings_file_path: str) -> Dict[str, Any]:
        """
        从 settings.py 文件加载并应用默认值（不做结构验证）

        Args:
            settings_file_path: settings.py 文件路径（绝对路径）

        Returns:
            Dict[str, Any]: 处理后的 settings 字典
        """
        # 这里将 settings_file_path 同时作为 settings_path 和 calculator_path 传入，
        # 对于 TagManager 来说，二者等价
        settings = SettingsProcessor.read_settings_file(
            settings_path=settings_file_path,
            calculator_path=settings_file_path,
        )
        SettingsProcessor.apply_defaults(settings)
        return settings

    def load_and_process_settings(
        self,
        settings_path: str,
        calculator_path: str,
    ) -> Dict[str, Any]:
        """
        加载并处理 settings 文件（完整流程）

        封装 SettingsProcessor.load_and_process_settings
        """
        return SettingsProcessor.load_and_process_settings(settings_path, calculator_path)

    # -------------------------------------------------------------------------
    # 验证 settings
    # -------------------------------------------------------------------------

    def validate_settings(self, settings: Dict[str, Any]) -> None:
        """
        验证 settings 是否有效（抛出异常）

        Args:
            settings: settings 字典

        Raises:
            ValueError: 如果验证失败
        """
        SettingsValidator.validate_all(settings)

    def is_valid_scenario_setting(self, scenario_setting: Dict[str, Any]) -> bool:
        """
        验证 scenario_setting 是否有效（返回 bool）

        职责：
        1. 验证 settings 基本结构
        2. 验证枚举值

        Args:
            scenario_setting: Scenario settings 字典，包含：
                - "settings": Dict[str, Any]

        Returns:
            bool: 如果有效返回 True，否则返回 False
        """
        if not isinstance(scenario_setting, dict):
            return False

        settings = scenario_setting.get("settings")
        if not settings:
            return False

        try:
            self.validate_settings(settings)
            return True
        except (ValueError, KeyError, TypeError):
            return False

    # -------------------------------------------------------------------------
    # 提取和处理配置
    # -------------------------------------------------------------------------

    def extract_calculator_config(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取 calculator 配置到字典（方便访问）
        """
        return SettingsProcessor.extract_calculator_config(settings)

    def process_tags_config(
        self,
        tags: List[Dict[str, Any]],
        calculator_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        处理 tags 配置（合并 calculator 和 tag 配置）
        """
        return SettingsProcessor.process_tags_config(tags, calculator_config)


# 创建单例实例，供外部直接使用
settings_manager = SettingsManager()