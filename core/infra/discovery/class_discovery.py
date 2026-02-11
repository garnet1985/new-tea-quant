"""
Class Discovery - 类自动发现工具

提供通用的类自动发现功能，支持：
1. 包扫描：扫描指定包下的所有子包/模块
2. 类发现：查找继承特定基类的类
3. 属性提取：从类中提取特定属性（如 provider_name, config_class）
4. 约定命名：支持命名约定（如 HandlerClassName + "Config"）
5. 缓存机制：缓存发现结果，避免重复扫描
"""
from typing import Dict, Type, Any, Optional, Callable, List, Set
from dataclasses import dataclass, field
import logging
import importlib
import pkgutil
import inspect


logger = logging.getLogger(__name__)


@dataclass
class DiscoveryResult:
    """发现结果"""
    classes: Dict[str, Type] = field(default_factory=dict)  # {key: class}
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元信息


@dataclass
class DiscoveryConfig:
    """
    发现配置
    
    Attributes:
        base_class: 基类（只发现继承此类的子类）
        module_name_pattern: 模块名模式（如 "{package}.{name}.provider"）
        class_filter: 类过滤函数（可选，用于额外过滤）
        key_extractor: 键提取函数（从类中提取唯一标识，如 provider_name）
        attribute_extractors: 属性提取器字典 {attr_name: extractor_func}
        skip_modules: 跳过的模块名集合（如 {"__pycache__", "_internal"}）
        skip_classes: 跳过的类名集合
    """
    base_class: Type
    module_name_pattern: str  # 例如: "{base_module}.{name}.provider"
    class_filter: Optional[Callable[[Type], bool]] = None
    key_extractor: Optional[Callable[[Type], str]] = None  # 从类中提取唯一标识
    attribute_extractors: Dict[str, Callable[[Type], Any]] = field(default_factory=dict)
    skip_modules: Set[str] = field(default_factory=lambda: {"__pycache__", "__init__"})
    skip_classes: Set[str] = field(default_factory=lambda: set())


class ClassDiscovery:
    """
    类自动发现工具
    
    使用示例：
        # 发现所有 Provider 类
        config = DiscoveryConfig(
            base_class=BaseProvider,
            module_name_pattern="userspace.data_source.providers.{name}.provider",
            key_extractor=lambda cls: getattr(cls, 'provider_name', None),
            class_filter=lambda cls: hasattr(cls, 'provider_name') and cls.provider_name
        )
        discovery = ClassDiscovery(config)
        result = discovery.discover("userspace.data_source.providers")
        # result.classes = {"tushare": TushareProvider, "akshare": AKShareProvider}
    """
    
    def __init__(self, config: DiscoveryConfig):
        """
        初始化发现器
        
        Args:
            config: 发现配置
        """
        self.config = config
        self._cache: Dict[str, DiscoveryResult] = {}  # 缓存发现结果
    
    def discover(
        self, 
        base_module_path: str,
        use_cache: bool = True
    ) -> DiscoveryResult:
        """
        发现指定包下的所有类
        
        Args:
            base_module_path: 基础模块路径（如 "userspace.data_source.providers"）
            use_cache: 是否使用缓存
        
        Returns:
            DiscoveryResult: 发现结果
        """
        cache_key = base_module_path
        
        # 检查缓存
        if use_cache and cache_key in self._cache:
            logger.debug(f"使用缓存发现结果: {base_module_path}")
            return self._cache[cache_key]
        
        result = DiscoveryResult()
        
        try:
            # 导入基础包
            base_package = importlib.import_module(base_module_path)
            package_paths = base_package.__path__
            
            # 扫描所有子包
            for importer, modname, ispkg in pkgutil.iter_modules(package_paths):
                if not ispkg or modname in self.config.skip_modules or modname.startswith('_'):
                    continue
                
                # 构建模块路径
                module_path = self.config.module_name_pattern.format(
                    base_module=base_module_path,
                    name=modname
                )
                
                # 发现该模块中的类
                module_classes = self._discover_classes_in_module(module_path)
                
                # 合并结果
                for key, cls in module_classes.items():
                    if key in result.classes:
                        existing_class = result.classes[key]
                        logger.warning(
                            f"⚠️  发现重复的类标识 '{key}': "
                            f"{existing_class.__name__} 和 {cls.__name__}"
                        )
                    else:
                        result.classes[key] = cls
                        # 提取属性
                        for attr_name, extractor in self.config.attribute_extractors.items():
                            if attr_name not in result.metadata:
                                result.metadata[attr_name] = {}
                            result.metadata[attr_name][key] = extractor(cls)
            
            # 缓存结果
            if use_cache:
                self._cache[cache_key] = result
            
        except ImportError:
            logger.debug(f"包不存在，跳过: {base_module_path}")
        except Exception as e:
            logger.error(f"❌ 发现类失败 {base_module_path}: {e}")
        
        return result
    
    def _discover_classes_in_module(self, module_path: str) -> Dict[str, Type]:
        """
        发现指定模块中的所有类
        
        Args:
            module_path: 模块路径
        
        Returns:
            {key: class} 字典
        """
        classes = {}
        
        try:
            module = importlib.import_module(module_path)
        except ImportError:
            # 模块不存在，跳过
            return classes
        except Exception as e:
            logger.warning(f"导入模块失败 {module_path}: {e}")
            return classes
        
        # 遍历模块中的所有属性
        for attr_name in dir(module):
            if attr_name in self.config.skip_classes:
                continue
            
            attr = getattr(module, attr_name)
            
            # 检查是否是类
            if not isinstance(attr, type):
                continue
            
            # 检查是否继承基类
            if not issubclass(attr, self.config.base_class):
                continue
            
            # 排除基类本身
            if attr == self.config.base_class:
                continue
            
            # 应用类过滤器
            if self.config.class_filter and not self.config.class_filter(attr):
                continue
            
            # 提取键（唯一标识）
            if self.config.key_extractor:
                key = self.config.key_extractor(attr)
                if not key:
                    continue
            else:
                # 默认使用类名
                key = attr.__name__
            
            classes[key] = attr
        
        return classes
    
    def discover_class_by_path(
        self,
        class_path: str,
        base_class: Optional[Type] = None
    ) -> Optional[Type]:
        """
        通过完整路径发现单个类
        
        Args:
            class_path: 类的完整路径（如 "userspace.data_source.handlers.kline.KlineHandler"）
            base_class: 可选的基类验证（如果提供，会验证类是否继承此基类）
        
        Returns:
            类对象，如果未找到返回 None
        """
        try:
            module_path, class_name = class_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name, None)
            
            if not cls or not isinstance(cls, type):
                return None
            
            # 验证基类（如果提供）
            if base_class:
                try:
                    if not issubclass(cls, base_class):
                        return None
                except TypeError:
                    # 如果 base_class 不是类型，跳过验证
                    pass
            
            return cls
            
        except ImportError as e:
            # 模块不存在是正常情况（可能是 handler 未实现或已禁用），使用 DEBUG 级别
            logger.debug(f"模块不存在，跳过: {class_path} ({e})")
            return None
        except Exception as e:
            logger.warning(f"通过路径发现类失败 {class_path}: {e}")
            return None
    
    def discover_class_attribute(
        self,
        class_path: str,
        attribute_name: str,
        default: Any = None
    ) -> Any:
        """
        发现类的特定属性（如 config_class）
        
        支持两种策略：
        1. 从类中直接获取属性
        2. 从模块中按约定命名获取（如 HandlerClassName + "Config"）
        
        Args:
            class_path: 类的完整路径
            attribute_name: 属性名（如 "config_class"）
            default: 默认值
        
        Returns:
            属性值，如果未找到返回 default
        """
        # 策略 1: 从类中获取属性
        cls = self.discover_class_by_path(class_path, base_class=None)  # 不验证基类，因为可能不是 BaseHandlerConfig
        if cls and hasattr(cls, attribute_name):
            attr_value = getattr(cls, attribute_name)
            if attr_value is not None:
                return attr_value
        
        # 策略 2: 从模块中按约定命名获取
        # 例如：KlineHandler -> KlineHandlerConfig
        try:
            module_path, class_name = class_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            
            # 约定命名：ClassName + AttributeName（首字母大写）
            convention_name = class_name + attribute_name.capitalize()
            if hasattr(module, convention_name):
                return getattr(module, convention_name)
        except Exception:
            pass
        
        return default
    
    def clear_cache(self, base_module_path: Optional[str] = None):
        """
        清除缓存
        
        Args:
            base_module_path: 如果提供，只清除该路径的缓存；否则清除所有缓存
        """
        if base_module_path:
            self._cache.pop(base_module_path, None)
        else:
            self._cache.clear()


# ========== 便捷函数 ==========

def discover_subclasses(
    base_class: Type,
    base_module_path: str,
    module_name_pattern: str = "{base_module}.{name}",
    key_extractor: Optional[Callable[[Type], str]] = None,
    class_filter: Optional[Callable[[Type], bool]] = None
) -> Dict[str, Type]:
    """
    便捷函数：发现所有继承 base_class 的子类
    
    Args:
        base_class: 基类
        base_module_path: 基础模块路径
        module_name_pattern: 模块名模式
        key_extractor: 键提取函数
        class_filter: 类过滤函数
    
    Returns:
        {key: class} 字典
    """
    config = DiscoveryConfig(
        base_class=base_class,
        module_name_pattern=module_name_pattern,
        key_extractor=key_extractor,
        class_filter=class_filter
    )
    discovery = ClassDiscovery(config)
    result = discovery.discover(base_module_path)
    return result.classes
