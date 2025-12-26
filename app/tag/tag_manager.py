"""
Tag Manager - 统一管理所有 Calculator

职责：
1. 发现和加载所有 tag calculators
2. 检查 settings 文件存在性
3. 检查 calculator 是否启用
4. 管理 calculator 实例
5. 提供统一的接口访问 calculators
"""
from typing import Dict, List, Optional, Type
import os
import importlib.util
import warnings
from pathlib import Path
from app.tag.base_tag_calculator import BaseTagCalculator


class TagManager:
    """Tag Manager - 统一管理所有 Calculator"""
    
    def __init__(self, tags_root: str = None):
        """
        初始化 TagManager
        
        Args:
            tags_root: tags 根目录路径（默认：app/tag/tags）
        """
        if tags_root is None:
            # 默认路径：app/tag/tags
            current_file = Path(__file__)
            tags_root = current_file.parent / "tags"
        
        self.tags_root = Path(tags_root)
        self.calculators: Dict[str, Type[BaseTagCalculator]] = {}
        self.enabled_calculators: Dict[str, Type[BaseTagCalculator]] = {}  # 只包含启用的
        self._load_calculators()

    def _load_calculators(self):
        """
        发现所有 tag calculators
        
        遍历 tags 目录，查找所有 calculator.py 文件
        检查 settings 文件存在性和 calculator 是否启用
        """
        if not self.tags_root.exists():
            return
        
        # 遍历所有子目录
        for tag_dir in self.tags_root.iterdir():
            if not tag_dir.is_dir():
                continue
            
            # 查找 calculator.py
            calculator_file = tag_dir / "calculator.py"
            if not calculator_file.exists():
                continue
            
            # 检查 settings 文件是否存在
            settings_file = tag_dir / "settings.py"
            if not settings_file.exists():
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Calculator '{tag_dir.name}' 缺少 settings.py 文件，跳过"
                )
                continue
            
            # 检查 calculator 是否启用
            try:
                is_enabled = self._check_calculator_enabled(settings_file)
                if not is_enabled:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(
                        f"Calculator '{tag_dir.name}' 未启用 (is_enabled = False)，跳过"
                    )
                    continue
            except Exception as e:
                # 检查失败，记录错误但继续处理其他 calculators
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"检查 calculator '{tag_dir.name}' 启用状态失败: {e}",
                    exc_info=True
                )
                continue
            
            # 加载 calculator 类
            try:
                calculator_class = self._load_calculator(calculator_file)
                tag_name = tag_dir.name
                self.calculators[tag_name] = calculator_class
                self.enabled_calculators[tag_name] = calculator_class
            except Exception as e:
                # 记录错误但继续处理其他 calculators
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"加载 calculator 失败: {tag_dir.name}, 错误: {e}",
                    exc_info=True
                )
    
    def _check_calculator_enabled(self, settings_file: Path) -> bool:
        """
        检查 calculator 是否启用
        
        Args:
            settings_file: settings.py 文件路径
            
        Returns:
            bool: True 如果启用，False 如果未启用
            
        Raises:
            ValueError: settings 文件格式错误
        """
        # 动态导入模块
        spec = importlib.util.spec_from_file_location("tag_settings", settings_file)
        if spec is None or spec.loader is None:
            raise ValueError(f"无法加载 settings 文件: {settings_file}")
        
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except SyntaxError as e:
            raise ValueError(f"Settings 文件语法错误: {settings_file}\n{str(e)}")
        except Exception as e:
            raise ValueError(f"导入 settings 文件失败: {settings_file}\n{str(e)}")
        
        # 提取 Settings
        if not hasattr(module, "Settings"):
            raise ValueError(f"Settings 文件缺少 Settings 变量: {settings_file}")
        
        settings = module.Settings
        if not isinstance(settings, dict):
            raise ValueError(f"Settings 必须是字典类型，当前类型: {type(settings)}")
        
        # 检查 calculator.meta.is_enabled
        calculator = settings.get("calculator", {})
        calculator_meta = calculator.get("meta", {})
        
        if "is_enabled" not in calculator_meta:
            calculator_name = calculator_meta.get("name", "unknown")
            warnings.warn(
                f"Calculator '{calculator_name}' 缺少 is_enabled 字段，默认按 False 处理（跳过）",
                UserWarning
            )
            return False
        
        return calculator_meta.get("is_enabled", False)
    
    def _load_calculator(self, calculator_file: Path) -> Type[BaseTagCalculator]:
        """
        加载 calculator 类
        
        Args:
            calculator_file: calculator.py 文件路径
            
        Returns:
            Type[BaseTagCalculator]: Calculator 类
        """
        # 动态导入模块
        spec = importlib.util.spec_from_file_location("tag_calculator", calculator_file)
        if spec is None or spec.loader is None:
            raise ValueError(f"无法加载 calculator 文件: {calculator_file}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 查找继承自 BaseTagCalculator 的类
        calculator_class = None
        for name, obj in module.__dict__.items():
            if (isinstance(obj, type) and 
                issubclass(obj, BaseTagCalculator) and 
                obj != BaseTagCalculator):
                calculator_class = obj
                break
        
        if calculator_class is None:
            raise ValueError(
                f"Calculator 文件中没有找到继承自 BaseTagCalculator 的类: {calculator_file}"
            )
        
        return calculator_class
    
    def get_calculator(self, tag_name: str) -> Optional[Type[BaseTagCalculator]]:
        """
        获取指定 tag 的 calculator 类（只返回启用的）
        
        Args:
            tag_name: tag 名称（目录名）
            
        Returns:
            Type[BaseTagCalculator] 或 None
        """
        return self.enabled_calculators.get(tag_name)
    
    def list_tags(self, enabled_only: bool = True) -> List[str]:
        """
        列出所有可用的 tag 名称
        
        Args:
            enabled_only: 是否只返回启用的 tag（默认 True）
            
        Returns:
            List[str]: tag 名称列表
        """
        if enabled_only:
            return list(self.enabled_calculators.keys())
        else:
            return list(self.calculators.keys())
    
    def create_calculator(
        self,
        tag_name: str,
        data_mgr=None,
        data_source_mgr=None,
        tag_value_model=None
    ) -> Optional[BaseTagCalculator]:
        """
        创建指定 tag 的 calculator 实例
        
        Args:
            tag_name: tag 名称（目录名）
            data_mgr: DataManager 实例
            data_source_mgr: DataSourceManager 实例
            tag_value_model: TagValueModel 实例
            
        Returns:
            BaseTagCalculator 实例或 None
        """
        calculator_class = self.get_calculator(tag_name)
        if calculator_class is None:
            return None
        
        # 确定 settings 文件路径
        settings_path = "settings.py"  # 相对于 calculator 同级目录
        
        try:
            calculator = calculator_class(
                settings_path=settings_path,
                data_mgr=data_mgr,
                data_source_mgr=data_source_mgr,
                tag_value_model=tag_value_model
            )
            return calculator
        except ValueError as e:
            # 可能是 is_enabled = False，记录但不抛出异常
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Tag '{tag_name}' 未启用或被跳过: {e}")
            return None
        except Exception as e:
            # 其他错误，记录并抛出
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"创建 calculator 失败: {tag_name}, 错误: {e}", exc_info=True)
            raise
    
    def reload(self):
        """
        重新发现所有 calculators
        
        用于动态加载新添加的 tag
        """
        self.calculators.clear()
        self._discover_calculators()
