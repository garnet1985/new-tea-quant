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
        mock_handler_config = Mock()
        # 使用 getattr 模拟行为
        def mock_getattr(name, default=None):
            if name == "test_param":
                return "test_value"
            elif name == "other_param":
                return None
            return default
        
        mock_handler_config.__getattr__ = lambda self, name: mock_getattr(name)
        type(mock_handler_config).test_param = "test_value"
        type(mock_handler_config).other_param = None
        
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
        # get_param 使用 getattr，对于不存在的属性会返回 default
        result = handler.get_param("non_existent", "default")
        assert result == "default"
        
        # 测试获取值为 None 的参数
        # get_param 的实现：如果 value is not None 才返回，否则返回 default
        # 所以 other_param 为 None 时，应该返回 default
        result = handler.get_param("other_param", "default")
        assert result == "default"
    
    def test_get_handler_config_with_apis(self):
        """测试获取 HandlerConfig（包含 API 配置）"""
        from core.modules.data_source.base_data_source_handler import BaseDataSourceHandler
        from core.modules.data_source.data_classes import DataSourceDefinition
        
        mock_schema = Mock()
        mock_handler_config = Mock()
        mock_handler_config.apis = {}
        
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
        from core.modules.data_source.data_classes.handler_config import BaseHandlerConfig
        
        mock_schema = Mock()
        mock_handler_config = Mock(spec=BaseHandlerConfig)
        
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
