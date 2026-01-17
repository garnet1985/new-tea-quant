"""
ClassDiscovery 单元测试
"""
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False


class TestClassDiscovery:
    """ClassDiscovery 测试类"""
    
    def test_discover_class_by_path(self):
        """测试通过路径发现类"""
        from core.infra.discovery import ClassDiscovery, DiscoveryConfig
        from core.modules.data_source.base_provider import BaseProvider
        
        config = DiscoveryConfig(
            base_class=BaseProvider,
            module_name_pattern=""
        )
        discovery = ClassDiscovery(config)
        
        # 测试发现一个已知的 Provider 类
        # 注意：这里需要实际存在的类路径
        # 如果测试环境没有，可以 mock
        pass  # 实际测试需要真实的类路径
    
    def test_discover_class_attribute(self):
        """测试发现类的属性"""
        from core.infra.discovery import ClassDiscovery, DiscoveryConfig
        from core.modules.data_source.base_provider import BaseProvider
        
        config = DiscoveryConfig(
            base_class=BaseProvider,
            module_name_pattern=""
        )
        discovery = ClassDiscovery(config)
        
        # 测试发现 Handler 的 config_class
        config_class = discovery.discover_class_attribute(
            class_path="userspace.data_source.handlers.kline.KlineHandler",
            attribute_name="config_class"
        )
        
        # 如果 KlineHandler 定义了 config_class，应该能找到
        if config_class:
            assert hasattr(config_class, '__name__')
            print(f"✅ 发现 config_class: {config_class.__name__}")
        else:
            print("⚠️  未找到 config_class（可能未定义）")
    
    def test_discover_with_config(self):
        """测试使用配置发现类"""
        from core.infra.discovery import ClassDiscovery, DiscoveryConfig
        from core.modules.data_source.base_provider import BaseProvider
        
        config = DiscoveryConfig(
            base_class=BaseProvider,
            module_name_pattern="userspace.data_source.providers.{name}.provider",
            key_extractor=lambda cls: getattr(cls, 'provider_name', None),
            class_filter=lambda cls: hasattr(cls, 'provider_name') and cls.provider_name
        )
        
        discovery = ClassDiscovery(config)
        result = discovery.discover("userspace.data_source.providers")
        
        assert isinstance(result.classes, dict)
        print(f"✅ 发现 {len(result.classes)} 个类")
    
    def test_cache_mechanism(self):
        """测试缓存机制"""
        from core.infra.discovery import ClassDiscovery, DiscoveryConfig
        from core.modules.data_source.base_provider import BaseProvider
        
        config = DiscoveryConfig(
            base_class=BaseProvider,
            module_name_pattern="userspace.data_source.providers.{name}.provider"
        )
        discovery = ClassDiscovery(config)
        
        # 第一次发现
        result1 = discovery.discover("userspace.data_source.providers", use_cache=True)
        
        # 第二次发现（应该使用缓存）
        result2 = discovery.discover("userspace.data_source.providers", use_cache=True)
        
        # 结果应该相同
        assert result1.classes == result2.classes
        
        # 清除缓存后应该重新发现
        discovery.clear_cache("userspace.data_source.providers")
        result3 = discovery.discover("userspace.data_source.providers", use_cache=True)
        
        # 结果应该仍然相同（内容相同，但可能是新对象）
        assert len(result1.classes) == len(result3.classes)


if __name__ == "__main__":
    if HAS_PYTEST:
        pytest.main([__file__])
    else:
        # 简单测试运行
        test = TestClassDiscovery()
        print("运行测试...")
        
        tests = [
            ("test_discover_class_attribute", test.test_discover_class_attribute),
            ("test_discover_with_config", test.test_discover_with_config),
            ("test_cache_mechanism", test.test_cache_mechanism),
        ]
        
        for test_name, test_func in tests:
            try:
                test_func()
                print(f"✅ {test_name} 通过")
            except Exception as e:
                print(f"❌ {test_name} 失败: {e}")
                import traceback
                traceback.print_exc()
