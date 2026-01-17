"""
DataSourceManager 单元测试
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
    # 如果没有 pytest，创建简单的测试框架
    class pytest:
        @staticmethod
        def fixture(func):
            return func


class TestDataSourceManager:
    """DataSourceManager 测试类"""
    
    def test_init(self):
        """测试初始化"""
        from core.modules.data_source.data_source_manager import DataSourceManager
        
        # 由于初始化会加载实际文件，这里只测试基本结构
        # 实际测试需要 mock 文件系统
        manager = DataSourceManager(is_verbose=False)
        
        assert hasattr(manager, '_schemas')
        assert hasattr(manager, '_handlers')
        assert hasattr(manager, '_mapping')
        assert hasattr(manager, '_definitions')
        assert hasattr(manager, 'data_manager')
    
    def test_load_handler_path_validation(self):
        """测试 Handler 路径验证"""
        from core.modules.data_source.data_source_manager import DataSourceManager
        
        manager = DataSourceManager(is_verbose=False)
        
        # 测试正确路径
        correct_path = "userspace.data_source.handlers.kline.KlineHandler"
        # 这里只测试路径格式验证逻辑，不实际导入
        
        # 测试错误路径
        wrong_path = "handlers.kline.KlineHandler"
        result = manager._load_handler("test", wrong_path)
        assert result is None  # 应该返回 None（路径格式错误）
    
    def test_get_definition(self):
        """测试获取 DataSourceDefinition"""
        from core.modules.data_source.data_source_manager import DataSourceManager
        
        manager = DataSourceManager(is_verbose=False)
        
        # 测试获取不存在的 definition
        result = manager.get_definition("non_existent")
        assert result is None
        
        # 测试获取存在的 definition（如果已加载）
        # 这需要实际的配置文件和 handler
    
    def test_list_data_sources(self):
        """测试列出所有数据源"""
        from core.modules.data_source.data_source_manager import DataSourceManager
        
        manager = DataSourceManager(is_verbose=False)
        
        # 测试返回类型
        result = manager.list_data_sources()
        assert isinstance(result, list)
    
    def test_get_handler_status(self):
        """测试获取 Handler 状态"""
        from core.modules.data_source.data_source_manager import DataSourceManager
        
        manager = DataSourceManager(is_verbose=False)
        
        status = manager.get_handler_status()
        
        assert isinstance(status, dict)
        assert "mapping_count" in status
        assert "enabled_count" in status
        assert "schema_count" in status
        assert "loaded_handlers" in status
        assert "failed_handlers" in status


if __name__ == "__main__":
    if HAS_PYTEST:
        pytest.main([__file__])
    else:
        # 简单测试运行
        test = TestDataSourceManager()
        print("运行测试...")
        try:
            test.test_init()
            print("✅ test_init 通过")
        except Exception as e:
            print(f"❌ test_init 失败: {e}")
        
        try:
            test.test_load_handler_path_validation()
            print("✅ test_load_handler_path_validation 通过")
        except Exception as e:
            print(f"❌ test_load_handler_path_validation 失败: {e}")
        
        try:
            test.test_get_definition()
            print("✅ test_get_definition 通过")
        except Exception as e:
            print(f"❌ test_get_definition 失败: {e}")
        
        try:
            test.test_list_data_sources()
            print("✅ test_list_data_sources 通过")
        except Exception as e:
            print(f"❌ test_list_data_sources 失败: {e}")
        
        try:
            test.test_get_handler_status()
            print("✅ test_get_handler_status 通过")
        except Exception as e:
            print(f"❌ test_get_handler_status 失败: {e}")
