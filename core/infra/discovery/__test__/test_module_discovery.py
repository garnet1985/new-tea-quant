"""
ModuleDiscovery 单元测试
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False


class TestModuleDiscovery:
    """ModuleDiscovery 测试类"""
    
    def test_discover_objects(self):
        """测试发现模块对象"""
        from core.infra.discovery import ModuleDiscovery
        
        discovery = ModuleDiscovery()
        
        # 测试发现 Schema
        schemas = discovery.discover_objects(
            base_module_path="userspace.data_source.handlers",
            object_name="SCHEMA",
            module_pattern="userspace.data_source.handlers.{name}.schema"
        )
        
        assert isinstance(schemas, dict)
        print(f"✅ 发现 {len(schemas)} 个 Schema 对象")
        
        # 验证 Schema 对象有 name 属性
        for handler_name, schema in schemas.items():
            if hasattr(schema, 'name'):
                print(f"  - {handler_name}: {schema.name}")
    
    def test_discover_modules_by_path(self):
        """测试通过路径发现模块"""
        from core.infra.discovery import ModuleDiscovery
        from core.infra.project_context import PathManager
        
        discovery = ModuleDiscovery()
        
        # 测试通过路径发现模块
        handlers_path = PathManager.data_source_handlers()
        modules = discovery.discover_modules_by_path(
            base_path=handlers_path,
            module_pattern="userspace.data_source.handlers.{name}",
            object_name=None  # 返回整个模块
        )
        
        assert isinstance(modules, dict)
        print(f"✅ 通过路径发现 {len(modules)} 个模块")


if __name__ == "__main__":
    if HAS_PYTEST:
        pytest.main([__file__])
    else:
        # 简单测试运行
        test = TestModuleDiscovery()
        print("运行测试...")
        
        tests = [
            ("test_discover_objects", test.test_discover_objects),
            ("test_discover_modules_by_path", test.test_discover_modules_by_path),
        ]
        
        for test_name, test_func in tests:
            try:
                test_func()
                print(f"✅ {test_name} 通过")
            except Exception as e:
                print(f"❌ {test_name} 失败: {e}")
                import traceback
                traceback.print_exc()
