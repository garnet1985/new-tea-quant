"""
BaseDataSourceHandler 单元测试
"""
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False


class TestBaseDataSourceHandler:
    """BaseDataSourceHandler 测试类"""
    
    def test_init_requires_definition(self):
        """测试初始化必须提供 definition"""
        from core.modules.data_source.base_data_source_handler import BaseDataSourceHandler
        from core.modules.data_source.data_classes import DataSourceDefinition
        
        # 创建测试 Handler 类（实现抽象方法）
        class TestHandler(BaseDataSourceHandler):
            data_source = "test"
            
            async def fetch(self, context):
                return []
            
            async def normalize(self, raw_data):
                return {"data": []}
        
        # 创建 mock schema
        mock_schema = Mock()
        mock_schema.name = "test_schema"
        
        # 测试不提供 definition 应该抛出异常
        try:
            handler = TestHandler(mock_schema, data_manager=None, definition=None)
            assert False, "应该抛出 ValueError"
        except ValueError as e:
            assert "必须提供 definition" in str(e)
    
    def test_validate_class_attributes(self):
        """测试类属性验证"""
        from core.modules.data_source.base_data_source_handler import BaseDataSourceHandler
        from core.modules.data_source.data_classes import DataSourceDefinition
        
        # 创建测试 Handler 类（没有定义 data_source）
        class TestHandler(BaseDataSourceHandler):
            async def fetch(self, context):
                return []
            
            async def normalize(self, raw_data):
                return {"data": []}
        
        mock_schema = Mock()
        mock_definition = Mock(spec=DataSourceDefinition)
        mock_definition.handler_config = None
        
        # 测试没有定义 data_source 应该抛出异常
        try:
            handler = TestHandler(mock_schema, data_manager=None, definition=mock_definition)
            assert False, "应该抛出 ValueError"
        except ValueError as e:
            assert "必须定义 data_source" in str(e)
    
    def test_get_param(self):
        """测试获取配置参数"""
        from core.modules.data_source.base_data_source_handler import BaseDataSourceHandler
        from core.modules.data_source.data_classes import DataSourceDefinition
        
        # 创建 mock schema
        mock_schema = Mock()
        
        # 创建 mock definition with handler_config
        # 使用普通对象而不是 Mock，以便设置属性
        class MockHandlerConfig:
            test_param = "test_value"
            other_param = None
            apis = {}  # 添加 apis 属性
        
        mock_handler_config = MockHandlerConfig()
        
        mock_definition = Mock(spec=DataSourceDefinition)
        mock_definition.handler_config = mock_handler_config
        
        # 创建测试 Handler
        class TestHandler(BaseDataSourceHandler):
            data_source = "test"
            
            async def fetch(self, context):
                return []
            
            async def normalize(self, raw_data):
                return {"data": []}
        
        handler = TestHandler(mock_schema, data_manager=None, definition=mock_definition)
        
        # 测试获取存在的参数
        assert handler.get_param("test_param") == "test_value"
        
        # 测试获取不存在的参数（使用默认值）
        result = handler.get_param("non_existent", "default")
        assert result == "default"
        
        # 测试获取值为 None 的参数
        # 注意：如果属性存在但值为 None，get_param 会返回 None（用户显式设置的 None）
        result = handler.get_param("other_param", "default")
        assert result is None  # 属性存在但值为 None，返回 None
    
    def test_get_handler_config_with_apis(self):
        """测试获取 HandlerConfig（包含 API 配置）"""
        from core.modules.data_source.base_data_source_handler import BaseDataSourceHandler
        from core.modules.data_source.data_classes import DataSourceDefinition
        
        mock_schema = Mock()
        # 使用普通对象而不是 Mock，避免迭代问题
        class MockHandlerConfig:
            apis = {}
        
        mock_handler_config = MockHandlerConfig()
        
        mock_definition = Mock(spec=DataSourceDefinition)
        mock_definition.handler_config = mock_handler_config
        
        class TestHandler(BaseDataSourceHandler):
            data_source = "test"
            
            async def fetch(self, context):
                return []
            
            async def normalize(self, raw_data):
                return {"data": []}
        
        handler = TestHandler(mock_schema, data_manager=None, definition=mock_definition)
        
        assert handler.get_handler_config() == mock_handler_config
    
    def test_get_handler_config(self):
        """测试获取 HandlerConfig"""
        from core.modules.data_source.base_data_source_handler import BaseDataSourceHandler
        from core.modules.data_source.data_classes import DataSourceDefinition
        
        mock_schema = Mock()
        # 使用普通对象而不是 Mock，避免迭代问题
        class MockHandlerConfig:
            apis = {}
        
        mock_handler_config = MockHandlerConfig()
        
        mock_definition = Mock(spec=DataSourceDefinition)
        mock_definition.handler_config = mock_handler_config
        
        class TestHandler(BaseDataSourceHandler):
            data_source = "test"
            
            async def fetch(self, context):
                return []
            
            async def normalize(self, raw_data):
                return {"data": []}
        
        handler = TestHandler(mock_schema, data_manager=None, definition=mock_definition)
        
        assert handler.get_handler_config() == mock_handler_config
    
    def test_create_simple_task(self):
        """测试创建简单 Task"""
        from core.modules.data_source.base_data_source_handler import BaseDataSourceHandler
        from core.modules.data_source.data_classes import DataSourceDefinition
        
        mock_schema = Mock()
        mock_definition = Mock(spec=DataSourceDefinition)
        mock_definition.handler_config = None
        
        class TestHandler(BaseDataSourceHandler):
            data_source = "test"
        
        handler = TestHandler(mock_schema, data_manager=None, definition=mock_definition)
        
        task = handler.create_simple_task(
            provider_name="tushare",
            method="get_stock_list",
            params={"fields": "ts_code,name"}
        )
        
        assert task.task_id == "test_task"
        assert len(task.api_jobs) == 1
        assert task.api_jobs[0].provider_name == "tushare"
        assert task.api_jobs[0].method == "get_stock_list"
        assert task.api_jobs[0].params == {"fields": "ts_code,name"}


if __name__ == "__main__":
    if HAS_PYTEST:
        pytest.main([__file__])
    else:
        # 简单测试运行
        test = TestBaseDataSourceHandler()
        print("运行测试...")
        
        tests = [
            ("test_init_requires_definition", test.test_init_requires_definition),
            ("test_validate_class_attributes", test.test_validate_class_attributes),
            ("test_get_param", test.test_get_param),
            ("test_get_handler_config", test.test_get_handler_config),
            ("test_get_handler_config", test.test_get_handler_config),
            ("test_create_simple_task", test.test_create_simple_task),
        ]
        
        for test_name, test_func in tests:
            try:
                test_func()
                print(f"✅ {test_name} 通过")
            except Exception as e:
                print(f"❌ {test_name} 失败: {e}")
                import traceback
                traceback.print_exc()
