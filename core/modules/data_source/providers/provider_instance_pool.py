"""
Provider 实例池

提供全局可访问的 Provider 实例管理，支持懒加载和多进程环境。
"""
from typing import Dict, Type, Any, Optional
from loguru import logger
import threading
import importlib
import pkgutil

from core.modules.data_source.base_provider import BaseProvider


class ProviderInstancePool:
    """
    Provider 实例池（单例模式）
    
    职责：
    - 管理所有 Provider 实例的创建和缓存
    - 懒加载：第一次使用时创建
    - 多进程安全：每个进程独立池子
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化池子（只执行一次）"""
        if self._initialized:
            return
        
        self._pool: Dict[str, BaseProvider] = {}  # Provider 实例缓存
        self._provider_classes: Dict[str, Type[BaseProvider]] = {}  # Provider 类注册表
        self._lock = threading.Lock()
        self._initialized = True
        
        # 初始化时扫描并缓存所有 Provider 类
        self._scan_and_cache_all_providers()
        
    def get_provider(
        self, 
        provider_name: str,
        config: Dict[str, Any] = None
    ) -> BaseProvider:
        """
        获取 Provider 实例（懒加载）
        
        Args:
            provider_name: Provider 名称（如 "tushare"）
            config: Provider 配置（如果为 None，会从配置文件读取）
        
        Returns:
            Provider 实例
        
        注意：
        - 不需要传递 provider_class，初始化时已扫描并缓存
        - Provider 实例懒加载：第一次使用时创建
        """
        # 检查池中是否已有实例
        if provider_name in self._pool:
            return self._pool[provider_name]
        
        # 创建新实例（加锁保证线程安全）
        with self._lock:
            # 双重检查（可能其他线程已经创建）
            if provider_name in self._pool:
                return self._pool[provider_name]
            
            # 获取或注册 Provider 类
            provider_class = self._get_provider_class(provider_name)
            
            # 创建并缓存
            if config is None:
                config = self._load_provider_config(provider_name)
            
            provider = provider_class(config)
            self._pool[provider_name] = provider
            
            return provider
    
    def _get_provider_class(self, provider_name: str) -> Type[BaseProvider]:
        """
        获取 Provider 类（从缓存中查找）
        
        Args:
            provider_name: Provider 名称
        
        Returns:
            Provider 类
        
        注意：
        - 初始化时已经扫描并缓存所有 Provider 类
        - 如果缓存中没有，_discover_provider 会自动重新扫描
        """
        provider_class = self._discover_provider(provider_name)
        if provider_class:
            return provider_class
        
        raise ValueError(
            f"Provider '{provider_name}' not found. "
            f"Available providers: {list(self._provider_classes.keys())}"
        )
    
    def _scan_and_cache_all_providers(self):
        """
        扫描并缓存所有 Provider 类（初始化时调用）
        
        扫描 userspace.data_source.providers 包，自动发现所有 Provider 实现。
        使用 pkgutil 扫描包结构，不依赖文件路径。
        """
        try:
            # 扫描 userspace.data_source.providers（优先级）
            try:
                userspace_providers_package = importlib.import_module('userspace.data_source.providers')
                userspace_package_path = userspace_providers_package.__path__
                self._scan_provider_package(userspace_package_path, 'userspace.data_source.providers')
            except ImportError:
                logger.debug("userspace.data_source.providers 包不存在，跳过")
            
            logger.info(
                f"✅ Scanned and cached {len(self._provider_classes)} providers: "
                f"{list(self._provider_classes.keys())}"
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to scan providers: {e}")
    
    def _scan_provider_package(self, package_path, base_module_path: str):
        """
        扫描指定包路径下的所有 Provider 类
        
        Args:
            package_path: 包路径（可以是列表）
            base_module_path: 基础模块路径（如 "userspace.data_source.providers"）
        """
        # 使用 pkgutil 遍历所有子包
        for importer, modname, ispkg in pkgutil.iter_modules(package_path):
            if not ispkg or modname.startswith('_'):
                continue
            
            # 尝试导入该子包的 provider 模块
            try:
                module_path = f'{base_module_path}.{modname}.provider'
                provider_module = importlib.import_module(module_path)
                
                # 查找所有继承 BaseProvider 的类
                for attr_name in dir(provider_module):
                    attr = getattr(provider_module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, BaseProvider) and
                        attr != BaseProvider and
                        hasattr(attr, 'provider_name') and
                        attr.provider_name):
                        
                        provider_name = attr.provider_name
                        if provider_name not in self._provider_classes:
                            self._provider_classes[provider_name] = attr
                        else:
                            # 如果 provider_name 重复，警告
                            existing_class = self._provider_classes[provider_name]
                            logger.warning(
                                f"⚠️  Duplicate provider_name '{provider_name}': "
                                f"{existing_class.__name__} and {attr.__name__}"
                            )
                            
            except ImportError:
                # 该目录没有 provider.py，跳过
                continue
            except Exception as e:
                logger.warning(f"Error scanning provider package '{modname}': {e}")
                continue
    
    def _discover_provider(self, provider_name: str) -> Optional[Type[BaseProvider]]:
        """
        获取 Provider 类（从缓存中查找）
        
        Args:
            provider_name: Provider 名称（类的 provider_name 属性）
        
        Returns:
            Provider 类，如果未找到返回 None
        
        注意：
        - 初始化时已经扫描并缓存所有 Provider 类
        - 如果缓存失效（多进程环境），可以调用 clear() 后重新扫描
        """
        # 从缓存中查找
        if provider_name in self._provider_classes:
            return self._provider_classes[provider_name]
        
        # 如果缓存中没有，可能是多进程环境导致缓存失效，尝试重新扫描
        logger.warning(
            f"Provider '{provider_name}' not found in cache. "
            f"This might be a multi-process issue. Re-scanning..."
        )
        self._scan_and_cache_all_providers()
        
        # 再次查找
        if provider_name in self._provider_classes:
            return self._provider_classes[provider_name]
        
        logger.warning(
            f"Provider '{provider_name}' not found. "
            f"Available providers: {list(self._provider_classes.keys())}"
        )
        return None
    
    def _load_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """
        从配置文件加载 Provider 配置
        
        Args:
            provider_name: Provider 名称（类的 provider_name 属性）
        
        Returns:
            Provider 配置字典
        
        注意：
        - 从 Provider 类所在的目录加载 config.py
        - auth_token.py 固定放在 provider 根目录下
        - 通过 Provider 类的模块路径直接构建 config 模块路径
        """
        # 获取 Provider 类
        if provider_name in self._provider_classes:
            provider_class = self._provider_classes[provider_name]
        else:
            # 如果还没注册，先发现 Provider（这会注册它）
            provider_class = self._discover_provider(provider_name)
            if not provider_class:
                logger.warning(f"Provider '{provider_name}' not found, cannot load config")
                return {}
        
        # 从 Provider 类的模块路径构建 config 模块路径
        # 例如：core.modules.data_source.providers.tushare.provider
        #   -> core.modules.data_source.providers.tushare.config
        provider_module_path = provider_class.__module__
        
        # 将模块路径中的最后一个部分（通常是 'provider'）替换为 'config'
        # 例如：'...tushare.provider' -> '...tushare.config'
        if provider_module_path.endswith('.provider'):
            config_module_path = provider_module_path[:-9] + '.config'  # 去掉 '.provider'，加上 '.config'
        else:
            # 如果模块路径不是以 '.provider' 结尾，尝试直接替换最后一个部分
            parts = provider_module_path.rsplit('.', 1)
            if len(parts) == 2:
                config_module_path = f"{parts[0]}.config"
            else:
                # 回退：尝试直接用 provider_name 构建路径
                config_module_path = f'core.modules.data_source.providers.{provider_name}.config'
        
        # 动态导入配置模块
        try:
            config_module = __import__(
                config_module_path,
                fromlist=['get_config']
            )
            
            # 调用配置模块的 get_config() 函数
            if hasattr(config_module, 'get_config'):
                return config_module.get_config()
            else:
                logger.warning(f"Provider '{provider_name}' config module has no get_config() function")
                return {}
        except ImportError as e:
            logger.warning(
                f"Failed to load config for '{provider_name}' "
                f"(tried module: {config_module_path}): {e}"
            )
            return {}
    
    def clear(self):
        """
        清空池子（用于测试或多进程环境）
        
        注意：
        - 清空实例缓存和类缓存
        - 多进程环境下，如果缓存失效，调用此方法后会自动重新扫描
        """
        with self._lock:
            self._pool.clear()
            self._provider_classes.clear()
            logger.debug("ProviderInstancePool cleared (instances and classes)")
    
    def refresh(self):
        """
        刷新 Provider 类缓存（用于多进程环境或动态加载）
        
        注意：
        - 清空类缓存并重新扫描
        - 实例缓存保持不变（可以继续使用）
        """
        with self._lock:
            self._provider_classes.clear()
            self._scan_and_cache_all_providers()
            logger.debug("ProviderInstancePool classes refreshed")
    
    def list_providers(self) -> list:
        """列出所有已缓存的 Provider 实例"""
        return list(self._pool.keys())
    
    def list_provider_classes(self) -> list:
        """列出所有已注册的 Provider 类"""
        return list(self._provider_classes.keys())
    
    def discover_all_providers(self) -> Dict[str, Type[BaseProvider]]:
        """
        重新扫描所有 Provider 类（手动触发）
        
        Returns:
            Provider 名称（provider_name）到类的映射
        
        注意：
        - 通常不需要手动调用，初始化时已经扫描
        - 可用于多进程环境或动态加载新 Provider
        """
        # 清空现有缓存
        self._provider_classes.clear()
        # 重新扫描
        self._scan_and_cache_all_providers()
        return self._provider_classes.copy()
    
    def __repr__(self):
        return f"<ProviderInstancePool(providers={list(self._pool.keys())})>"


# 全局访问函数
def get_provider_pool() -> ProviderInstancePool:
    """获取全局 ProviderInstancePool 实例"""
    return ProviderInstancePool()

