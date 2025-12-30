"""
Settings 处理器

提供静态方法用于读取、处理和合并 Tag Calculator 的 settings 配置。
"""
from typing import Dict, Any, List
import importlib.util
import os
from app.tag.core.enums import UpdateMode, VersionChangeAction


class SettingsProcessor:
    """Settings 配置处理器（静态方法）"""
    
    @staticmethod
    def read_settings_file(
        settings_path: str,
        calculator_path: str
    ) -> Dict[str, Any]:
        """
        读取 settings 文件（Python 文件）
        
        Args:
            settings_path: settings 文件路径（相对路径）
            calculator_path: calculator 文件路径
            
        Returns:
            Dict[str, Any]: Settings 字典
            
        Raises:
            FileNotFoundError: 文件不存在
            SyntaxError: 文件语法错误
            ValueError: 缺少 Settings 变量
        """
        # 转换为绝对路径
        if not os.path.isabs(settings_path):
            calculator_dir = os.path.dirname(os.path.abspath(calculator_path))
            settings_path = os.path.join(calculator_dir, settings_path)
        
        # 动态导入模块
        spec = importlib.util.spec_from_file_location("tag_settings", settings_path)
        if spec is None or spec.loader is None:
            raise ValueError(f"无法加载 settings 文件: {settings_path}")
        
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except SyntaxError as e:
            raise SyntaxError(f"Settings 文件语法错误: {settings_path}\n{str(e)}")
        except Exception as e:
            raise ValueError(f"导入 settings 文件失败: {settings_path}\n{str(e)}")
        
        # 提取 Settings 变量
        if not hasattr(module, "Settings"):
            raise ValueError(f"Settings 文件缺少 Settings 变量: {settings_path}")
        
        settings = module.Settings
        
        # 验证 Settings 是字典类型
        if not isinstance(settings, dict):
            raise ValueError(f"Settings 必须是字典类型，当前类型: {type(settings)}")
        
        return settings
    
    @staticmethod
    def apply_defaults(settings: Dict[str, Any]):
        """
        应用默认值
        
        Args:
            settings: settings 字典（会被修改）
        """
        # scenario 默认值
        scenario = settings["scenario"]
        if "display_name" not in scenario:
            scenario["display_name"] = scenario["name"]
        if "description" not in scenario:
            scenario["description"] = ""
        if "on_version_change" not in scenario:
            scenario["on_version_change"] = VersionChangeAction.REFRESH_SCENARIO.value
        
        # calculator 默认值
        calculator = settings["calculator"]
        if "required_terms" not in calculator or calculator["required_terms"] is None:
            calculator["required_terms"] = []
        if "required_data" not in calculator:
            calculator["required_data"] = []
        if "core" not in calculator:
            calculator["core"] = {}
        if "performance" not in calculator:
            calculator["performance"] = {}
        
        # calculator.performance 默认值
        perf = calculator["performance"]
        if "update_mode" not in perf:
            perf["update_mode"] = UpdateMode.INCREMENTAL.value
        # max_workers 不设置默认值，由系统自动分配
    
    @staticmethod
    def load_and_process_settings(
        settings_path: str,
        calculator_path: str
    ) -> Dict[str, Any]:
        """
        加载并处理 settings 文件（完整流程）
        
        Args:
            settings_path: settings 文件路径（相对路径）
            calculator_path: calculator 文件路径
            
        Returns:
            Dict[str, Any]: 处理后的 settings 字典
        """
        # 1. 读取 settings 文件
        settings = SettingsProcessor.read_settings_file(settings_path, calculator_path)
        
        # 2. 应用默认值
        SettingsProcessor.apply_defaults(settings)
        
        return settings
    
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
    
    @staticmethod
    def process_tags_config(
        tags: List[Dict[str, Any]],
        calculator_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        处理 tags 配置（合并 calculator 和 tag 配置）
        
        Args:
            tags: tags 配置列表
            calculator_config: calculator 配置字典
            
        Returns:
            List[Dict[str, Any]]: 处理后的 tags 配置列表
        """
        processed_tags = []
        
        for tag in tags:
            # 合并配置
            merged_config = SettingsProcessor.merge_tag_config(tag, calculator_config)
            processed_tags.append(merged_config)
        
        return processed_tags
    
    @staticmethod
    def extract_calculator_config(settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取 calculator 配置到字典（方便访问）
        
        Args:
            settings: settings 字典
            
        Returns:
            Dict[str, Any]: 提取的配置字典
                - scenario_name: str
                - scenario_version: str
                - base_term: str
                - required_terms: List[str]
                - required_data: List[str]
                - core: Dict[str, Any]
                - performance: Dict[str, Any]
        """
        scenario = settings["scenario"]
        calculator = settings["calculator"]
        
        return {
            "scenario_name": scenario["name"],
            "scenario_version": scenario["version"],
            "base_term": calculator["base_term"],
            "required_terms": calculator.get("required_terms", []),
            "required_data": calculator.get("required_data", []),
            "core": calculator.get("core", {}),
            "performance": calculator.get("performance", {}),
        }
