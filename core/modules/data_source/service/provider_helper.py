from typing import Any, Dict, Type

from loguru import logger


class DataSourceProviderHelper:
    """
    Provider 相关的辅助方法。

    职责：
    - 发现 userspace 下的 Provider 类
    - （如有需要）加载 Provider 配置
    - 使用配置实例化 Provider
    """

    @staticmethod
    def discover_provider_classes() -> Dict[str, Type[Any]]:
        """
        发现 userspace 下所有的 Provider 类。

        约定：
        - 扫描路径: userspace.data_source.providers
        - Provider 必须继承 BaseProvider，并声明 provider_name
        """
        from core.infra.discovery import ClassDiscovery, DiscoveryConfig
        from core.modules.data_source.base_class.base_provider import BaseProvider

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
