"""ClassDiscovery 单元测试。"""
from core.infra.discovery.core.class_discovery import ClassDiscovery, DiscoveryConfig
from core.modules.data_source.base_class.base_provider import BaseProvider


def test_discover_class_attribute():
    discovery = ClassDiscovery(
        DiscoveryConfig(base_class=BaseProvider, module_name_pattern="")
    )
    config_class = discovery.discover_class_attribute(
        class_path="userspace.extensions.data_source.handlers.kline.KlineHandler",
        attribute_name="config_class",
    )
    if config_class is not None:
        assert hasattr(config_class, "__name__")


def test_discover_with_config():
    config = DiscoveryConfig(
        base_class=BaseProvider,
        module_name_pattern="userspace.extensions.data_source.providers.{name}.provider",
        key_extractor=lambda cls: getattr(cls, "provider_name", None),
        class_filter=lambda cls: hasattr(cls, "provider_name") and cls.provider_name,
    )
    discovery = ClassDiscovery(config)
    result = discovery.discover("userspace.extensions.data_source.providers")
    assert isinstance(result.classes, dict)


def test_cache_mechanism():
    config = DiscoveryConfig(
        base_class=BaseProvider,
        module_name_pattern="userspace.extensions.data_source.providers.{name}.provider",
    )
    discovery = ClassDiscovery(config)
    result1 = discovery.discover(
        "userspace.extensions.data_source.providers", use_cache=True
    )
    result2 = discovery.discover(
        "userspace.extensions.data_source.providers", use_cache=True
    )
    assert result1.classes == result2.classes

    discovery.clear_cache("userspace.extensions.data_source.providers")
    result3 = discovery.discover(
        "userspace.extensions.data_source.providers", use_cache=True
    )
    assert len(result1.classes) == len(result3.classes)
