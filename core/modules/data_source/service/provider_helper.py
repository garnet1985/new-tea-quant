from typing import Any, Dict, Type, Optional
import threading
import logging

from core.modules.data_source.base_class.base_provider import BaseProvider


logger = logging.getLogger(__name__)


class DataSourceProviderHelper:
    """
    Provider 相关的辅助方法。

    职责：
    - 发现 userspace 下的 Provider 类
    - 使用配置实例化 Provider
    - 提供全局懒加载的 Provider 实例访问（单例模式）
    """

    # Provider 实例缓存（懒加载）
    _provider_instances: Dict[str, BaseProvider] = {}
    # Provider 类缓存
    _provider_classes: Dict[str, Type[BaseProvider]] = {}
    _classes_lock = threading.Lock()

    @staticmethod
    def discover_provider_classes() -> Dict[str, Type[Any]]:
        """
        发现 userspace 下所有的 Provider 类。

        约定：
        - 扫描路径: userspace.data_source.providers
        - Provider 必须继承 BaseProvider，并声明 provider_name
        """
        from core.infra.discovery import ClassDiscovery, DiscoveryConfig

        config = DiscoveryConfig(
            base_class=BaseProvider,
            module_name_pattern="userspace.data_source.providers.{name}.provider",
            key_extractor=lambda cls: getattr(cls, "provider_name", None),
            class_filter=lambda cls: (
                hasattr(cls, "provider_name")
                and getattr(cls, "provider_name") is not None
            ),
            skip_modules={"__pycache__", "__init__"},
        )

        discovery = ClassDiscovery(config)
        result = discovery.discover("userspace.data_source.providers")

        return result.classes

    @staticmethod
    def create_provider_instance(provider_name: str, provider_class: Type[Any]) -> Any:
        """
        使用默认配置实例化 Provider。

        约定：
        - 不再显式传入 config，由 BaseProvider 在 config=None 时通过 _load_default_config 负责认证等配置加载。
        """
        try:
            return provider_class(None)
        except Exception as e:
            logger.error(f"❌ 初始化 Provider '{provider_name}' 失败: {e}")
            return None

    @classmethod
    def get_provider(cls, provider_name: str, config: Dict[str, Any] = None) -> BaseProvider:
        """
        获取 Provider 实例（懒加载，全局单例缓存）。

        这是 ProviderInstancePool 的替代方法，提供全局访问点。

        Args:
            provider_name: Provider 名称（如 "tushare"）
            config: Provider 配置（如果为 None，BaseProvider 会自动加载默认配置）

        Returns:
            Provider 实例

        注意：
        - 懒加载：第一次使用时创建并缓存
        - 线程安全：使用锁保证并发安全
        - 配置加载由 BaseProvider 统一处理（通过 _load_default_config）
        """
        # 检查缓存中是否已有实例
        if provider_name in cls._provider_instances:
            return cls._provider_instances[provider_name]

        # 创建新实例（加锁保证线程安全）
        with cls._classes_lock:
            # 双重检查（可能其他线程已经创建）
            if provider_name in cls._provider_instances:
                return cls._provider_instances[provider_name]

            # 获取或发现 Provider 类
            provider_class = cls._get_provider_class(provider_name)
            if not provider_class:
                raise ValueError(
                    f"Provider '{provider_name}' not found. "
                    f"Available providers: {list(cls._provider_classes.keys())}"
                )

            # 创建并缓存（传递 None 让 BaseProvider 自动加载配置）
            provider = provider_class(config)
            cls._provider_instances[provider_name] = provider

            return provider

    @classmethod
    def _get_provider_class(cls, provider_name: str) -> Optional[Type[BaseProvider]]:
        """
        获取 Provider 类（从缓存中查找，如果不存在则发现）。

        Args:
            provider_name: Provider 名称

        Returns:
            Provider 类，如果未找到返回 None
        """
        # 从缓存中查找
        if provider_name in cls._provider_classes:
            return cls._provider_classes[provider_name]

        # 如果缓存中没有，发现并缓存所有 Provider 类
        provider_classes = cls.discover_provider_classes()
        cls._provider_classes.update(provider_classes)

        # 再次查找
        return cls._provider_classes.get(provider_name)

    @classmethod
    def clear_cache(cls):
        """
        清空 Provider 实例和类缓存（用于测试或多进程环境）。
        """
        with cls._classes_lock:
            cls._provider_instances.clear()
            cls._provider_classes.clear()
            logger.debug("Provider cache cleared")

    @classmethod
    def refresh_classes(cls):
        """
        刷新 Provider 类缓存（用于多进程环境或动态加载）。

        注意：
        - 清空类缓存并重新扫描
        - 实例缓存保持不变（可以继续使用）
        """
        with cls._classes_lock:
            cls._provider_classes.clear()
            provider_classes = cls.discover_provider_classes()
            cls._provider_classes.update(provider_classes)
            logger.debug("Provider classes refreshed")
