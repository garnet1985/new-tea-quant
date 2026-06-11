"""
BaseHandler 单元测试（当前 API：data_source_key, schema dict, config, providers）
"""
from unittest.mock import MagicMock, Mock


class TestBaseHandler:
    """BaseHandler 测试类（与 base_class.base_handler 当前 API 一致）"""

    def test_init_and_get_key(self):
        """测试初始化与 get_key"""
        from core.modules.data_source.base_class.base_handler import BaseHandler
        from core.modules.data_source.data_class.config import DataSourceConfig

        schema = {"name": "test_table", "fields": [{"name": "id", "type": "string"}]}
        config_dict = {
            "table": "sys_test",
            "save_mode": "unified",
            "renew": {
                "type": "incremental",
                "last_update_info": {"date_field": "date", "date_format": "day"},
                "job_execution": {"list": "stock_list", "key": "id"},
            },
            "apis": {"api1": {"provider_name": "tushare", "method": "get_xxx"}},
        }
        config = DataSourceConfig.from_dict(config_dict, "test_key")
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
        config = DataSourceConfig.from_dict(
            {
                "table": "t",
                "save_mode": "unified",
                "renew": {
                    "type": "incremental",
                    "last_update_info": {"date_field": "date", "date_format": "day"},
                    "job_execution": {"list": "x", "key": "id"},
                },
                "apis": {"a": {"provider_name": "p", "method": "m"}},
            },
            "k",
        )
        handler = BaseHandler(
            data_source_key="k",
            schema=schema,
            config=config,
            providers={},
            depend_on_data_source_names=["stock_list", "latest_completed_trading_date"],
        )
        assert handler.get_dependency_data_source_names() == [
            "stock_list",
            "latest_completed_trading_date",
        ]

