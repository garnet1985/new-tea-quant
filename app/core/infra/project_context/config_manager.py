"""
Config Manager - 配置管理器

职责：处理默认配置和用户配置的加载与合并。

设计原则：
- 配置合并逻辑复用 utils/util.py 的 deep_merge_config
- 支持 JSON 和 Python 两种文件格式
- Python 文件支持动态导入（importlib）
- 提供静态方法，无状态
"""

from pathlib import Path
from typing import Dict, Any, Set, Optional
import json
import importlib
import importlib.util
import sys
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器 - 处理默认配置和用户配置的合并"""
    
    @staticmethod
    def load_with_defaults(
        default_path: Path,
        user_path: Path,
        deep_merge_fields: Set[str] = None,
        override_fields: Set[str] = None,
        file_type: str = "json"
    ) -> Dict[str, Any]:
        """
        加载配置（用户配置覆盖默认配置）
        
        内部调用 utils/util.py 的 deep_merge_config
        
        Args:
            default_path: 默认配置文件路径
            user_path: 用户配置文件路径（可选，如果不存在则只返回默认配置）
            deep_merge_fields: 需要深度合并的字段名集合
            override_fields: 需要完全覆盖的字段名集合
            file_type: 文件类型（"json" 或 "py"）
        
        Returns:
            合并后的配置字典
        
        Example:
            default_settings = Path("core/modules/strategy/default_settings.json")
            user_settings = Path("userspace/strategies/example/settings.py")
            settings = ConfigManager.load_with_defaults(
                default_settings,
                user_settings,
                deep_merge_fields={"params"},
                file_type="py"
            )
        """
        # 1. 加载默认配置
        defaults = ConfigManager._load_file(default_path, file_type)
        if not defaults:
            defaults = {}
        
        # 2. 加载用户配置（如果存在）
        if user_path.exists():
            user_config = ConfigManager._load_file(user_path, file_type)
            if user_config:
                # 3. 调用 utils/util.py 的合并逻辑
                try:
                    from utils.util import deep_merge_config
                    return deep_merge_config(
                        defaults,
                        user_config,
                        deep_merge_fields=deep_merge_fields,
                        override_fields=override_fields
                    )
                except ImportError:
                    logger.warning(
                        f"无法导入 utils.util.deep_merge_config，使用浅层合并"
                    )
                    # Fallback: 浅层合并
                    return {**defaults, **user_config}
        
        return defaults
    
    @staticmethod
    def load_json(path: Path) -> Dict[str, Any]:
        """
        加载 JSON 配置文件
        
        Args:
            path: JSON 文件路径
        
        Returns:
            配置字典，如果文件不存在或加载失败返回空字典
        """
        return ConfigManager._load_file(path, "json") or {}
    
    @staticmethod
    def load_python(path: Path, var_name: str = "settings") -> Dict[str, Any]:
        """
        加载 Python 配置文件（如 settings.py）
        
        Args:
            path: Python 文件路径
            var_name: 配置变量名（默认为 "settings"）
        
        Returns:
            配置字典，如果文件不存在或加载失败返回空字典
        
        Example:
            # settings.py 中定义：
            # settings = {"name": "example", "params": {...}}
            
            config = ConfigManager.load_python(
                Path("userspace/strategies/example/settings.py"),
                var_name="settings"
            )
        """
        result = ConfigManager._load_file(path, "py", var_name=var_name)
        return result if isinstance(result, dict) else {}
    
    @staticmethod
    def _load_file(
        path: Path,
        file_type: str,
        var_name: str = "settings"
    ) -> Optional[Any]:
        """
        内部方法：加载文件
        
        Args:
            path: 文件路径
            file_type: 文件类型（"json" 或 "py"）
            var_name: Python 文件的变量名（仅用于 "py" 类型）
        
        Returns:
            加载的内容，失败返回 None
        """
        if not path.exists():
            return None
        
        try:
            if file_type == "json":
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            
            elif file_type == "py":
                # 转换为绝对路径
                if not path.is_absolute():
                    path = path.resolve()
                
                # 动态导入 Python 文件
                module_name = f"_config_module_{path.stem}_{id(path)}"
                
                # 使用 importlib.util 加载模块
                spec = importlib.util.spec_from_file_location(module_name, path)
                if spec is None or spec.loader is None:
                    logger.warning(f"无法加载 Python 配置文件: {path}")
                    return None
                
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                # 获取配置变量
                if hasattr(module, var_name):
                    config = getattr(module, var_name)
                    # 确保返回字典
                    if isinstance(config, dict):
                        return config
                    else:
                        logger.warning(
                            f"Python 配置文件中的 {var_name} 不是字典类型: {path}"
                        )
                        return None
                else:
                    logger.warning(
                        f"Python 配置文件中没有找到变量 {var_name}: {path}"
                    )
                    return None
            
            else:
                logger.warning(f"不支持的文件类型: {file_type}")
                return None
        
        except Exception as e:
            logger.warning(f"加载配置文件失败: {path}, error={e}")
            return None
