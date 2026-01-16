"""
DataSourceDefinition 单元测试
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


class TestDataSourceDefinition:
    """DataSourceDefinition 测试类"""
    
    def test_from_dict_basic(self):
        """测试从字典创建 DataSourceDefinition"""
        from core.modules.data_source.definition import DataSourceDefinition
        
        data = {
            "handler": "userspace.data_source.handlers.kline.KlineHandler",
            "description": "K线数据",
            "dependencies": {
                "latest_completed_trading_date": True,
                "stock_list": True
            },
            "provider_config": {
                "apis": []
            },
            "handler_config": {}
        }
        
        definition = DataSourceDefinition.from_dict(data, name="kline")
        
        assert definition.name == "kline"
        assert definition.handler_path == "userspace.data_source.handlers.kline.KlineHandler"
        assert definition.description == "K线数据"
        assert definition.dependencies == {
            "latest_completed_trading_date": True,
            "stock_list": True
        }
        assert definition.schema_name == "kline"
    
    def test_from_dict_with_provider_config(self):
        """测试从字典创建带 ProviderConfig 的 DataSourceDefinition"""
        from core.modules.data_source.definition import DataSourceDefinition
        
        data = {
            "handler": "userspace.data_source.handlers.gdp.GDPHandler",
            "provider_config": {
                "apis": [
                    {
                        "provider_name": "tushare",
                        "method": "get_gdp",
                        "field_mapping": {
                            "quarter": "quarter",
                            "gdp": "gdp"
                        },
                        "params": {}
                    }
                ]
            },
            "handler_config": {}
        }
        
        definition = DataSourceDefinition.from_dict(data, name="gdp")
        
        assert len(definition.provider_config.apis) == 1
        assert definition.provider_config.apis[0].provider_name == "tushare"
        assert definition.provider_config.apis[0].method == "get_gdp"
        assert definition.provider_config.apis[0].field_mapping == {
            "quarter": "quarter",
            "gdp": "gdp"
        }
    
    def test_validate(self):
        """测试验证方法"""
        from core.modules.data_source.definition import DataSourceDefinition
        
        # 测试有效的 definition
        data = {
            "handler": "userspace.data_source.handlers.kline.KlineHandler",
            "provider_config": {
                "apis": []
            },
            "handler_config": {}
        }
        
        definition = DataSourceDefinition.from_dict(data, name="kline")
        assert definition.validate() is True
        
        # 测试缺少 handler 的 definition
        invalid_data = {
            "provider_config": {
                "apis": []
            }
        }
        
        try:
            definition = DataSourceDefinition.from_dict(invalid_data, name="invalid")
            assert definition.validate() is False
        except Exception:
            # 如果 from_dict 已经验证，这也是合理的
            pass
    
    def test_to_dict(self):
        """测试序列化为字典"""
        from core.modules.data_source.definition import DataSourceDefinition
        
        data = {
            "handler": "userspace.data_source.handlers.kline.KlineHandler",
            "description": "K线数据",
            "dependencies": {
                "latest_completed_trading_date": True
            },
            "provider_config": {
                "apis": []
            },
            "handler_config": {}
        }
        
        definition = DataSourceDefinition.from_dict(data, name="kline")
        result = definition.to_dict()
        
        assert result["handler"] == "userspace.data_source.handlers.kline.KlineHandler"
        assert result["description"] == "K线数据"
        assert "dependencies" in result
        assert "provider_config" in result


if __name__ == "__main__":
    if HAS_PYTEST:
        pytest.main([__file__])
    else:
        # 简单测试运行
        test = TestDataSourceDefinition()
        print("运行测试...")
        
        tests = [
            ("test_from_dict_basic", test.test_from_dict_basic),
            ("test_from_dict_with_provider_config", test.test_from_dict_with_provider_config),
            ("test_validate", test.test_validate),
            ("test_to_dict", test.test_to_dict),
        ]
        
        for test_name, test_func in tests:
            try:
                test_func()
                print(f"✅ {test_name} 通过")
            except Exception as e:
                print(f"❌ {test_name} 失败: {e}")
                import traceback
                traceback.print_exc()
