"""
BaseHandler 单元测试（当前 API：data_source_key, schema dict, config, providers）
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


class TestBaseHandler:
    """BaseHandler 测试类（与 base_class.base_handler 当前 API 一致）"""

    def test_init_and_get_key(self):
        """测试初始化与 get_key"""
        from core.modules.data_source.base_class.base_handler import BaseHandler
        from core.modules.data_source.data_class.config import DataSourceConfig

        schema = {"name": "test_table", "fields": [{"name": "id", "type": "string"}]}
        config_dict = {
            "table": "sys_test",
            "renew": {"type": "incremental", "last_update_info": {"date_field": "date", "date_format": "day"}},
            "result_group_by": {"list": "stock_list", "by_key": "id"},
            "apis": {"api1": {"provider_name": "tushare", "method": "get_xxx", "max_per_minute": 100}},
        }
        config = DataSourceConfig(config_dict, data_source_key="test_key")
        providers = {}

        handler = BaseHandler(
            data_source_key="test_key",
            schema=schema,
            config=config,
            providers=providers,
            depend_on_data_source_names=[],
        )
        assert handler.get_key() == "test_key"
        assert handler.context.get("schema") == schema
        assert handler.context.get("config") is config

    def test_get_dependency_data_source_names(self):
        """测试 get_dependency_data_source_names"""
        from core.modules.data_source.base_class.base_handler import BaseHandler
        from core.modules.data_source.data_class.config import DataSourceConfig

        schema = {"name": "t", "fields": []}
        config = DataSourceConfig(
            {"table": "t", "renew": {"type": "incremental", "last_update_info": {}}, "result_group_by": {"list": "x", "by_key": "id"}, "apis": {"a": {"provider_name": "p", "method": "m", "max_per_minute": 1}}},
            data_source_key="k",
        )
        handler = BaseHandler(
            data_source_key="k",
            schema=schema,
            config=config,
            providers={},
            depend_on_data_source_names=["stock_list", "latest_trading_date"],
        )
        assert handler.get_dependency_data_source_names() == ["stock_list", "latest_trading_date"]


if __name__ == "__main__":
    if HAS_PYTEST:
        pytest.main([__file__])
    else:
        test = TestBaseHandler()
        for name in ["test_init_and_get_key", "test_get_dependency_data_source_names"]:
            try:
                getattr(test, name)()
                print(f"✅ {name} 通过")
            except Exception as e:
                print(f"❌ {name} 失败: {e}")
