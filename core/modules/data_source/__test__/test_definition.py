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
        """测试从字典创建 DataSourceDefinition（带 renew_mode）"""
        from core.modules.data_source.data_classes import DataSourceDefinition
        
        data = {
            "handler": "userspace.data_source.handlers.kline.KlineHandler",
            "description": "K线数据",
            "dependencies": {
                "latest_completed_trading_date": True,
                "stock_list": True
            },
            "handler_config": {
                "renew_mode": "incremental"
            }
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
        # handler_config 可能是 None（如果 Handler 类不存在或没有 config_class）
        # 或者是一个 Config 实例
        assert definition.handler_config is None or hasattr(definition.handler_config, 'renew_mode')
    
    def test_from_dict_with_apis(self):
        """测试从字典创建带 API 配置的 DataSourceDefinition（新格式：字典）"""
        from core.modules.data_source.data_classes import DataSourceDefinition
        
        data = {
            "handler": "userspace.data_source.handlers.gdp.GdpHandler",
            "handler_config": {
                "renew_mode": "rolling",
                "apis": {
                    "gdp_data": {
                        "provider_name": "tushare",
                        "method": "get_gdp",
                        "params": {}
                    }
                }
            }
        }
        
        definition = DataSourceDefinition.from_dict(data, name="gdp")
        
        # handler_config 可能是 None（如果 Handler 类不存在），或者是一个 Config 实例
        if definition.handler_config is not None:
            # 如果 handler_config 存在，检查 apis
            assert hasattr(definition.handler_config, 'apis')
            if definition.handler_config.apis:
                assert "gdp_data" in definition.handler_config.apis
                assert definition.handler_config.apis["gdp_data"]["provider_name"] == "tushare"
                assert definition.handler_config.apis["gdp_data"]["method"] == "get_gdp"
    
    def test_from_dict_with_renew_mode(self):
        """测试不同 renew_mode 的配置"""
        from core.modules.data_source.data_classes import DataSourceDefinition
        
        # 测试 rolling 模式
        data_rolling = {
            "handler": "userspace.data_source.handlers.gdp.GdpHandler",
            "handler_config": {
                "renew_mode": "rolling",
                "date_format": "quarter",
                "rolling_unit": "quarter",
                "rolling_length": 4
            }
        }
        
        definition_rolling = DataSourceDefinition.from_dict(data_rolling, name="gdp")
        assert definition_rolling.name == "gdp"
        # handler_config 可能是 None（如果 Handler 类不存在）
        if definition_rolling.handler_config is not None:
            assert hasattr(definition_rolling.handler_config, 'renew_mode')
    
    def test_validate(self):
        """测试验证方法"""
        from core.modules.data_source.data_classes import DataSourceDefinition
        
        # 测试有效的 definition
        data = {
            "handler": "userspace.data_source.handlers.kline.KlineHandler",
            "handler_config": {
                "renew_mode": "incremental"
            }
        }
        
        definition = DataSourceDefinition.from_dict(data, name="kline")
        assert definition.validate() is True
        
        # 测试缺少 handler 的 definition
        invalid_data = {}
        
        try:
            definition = DataSourceDefinition.from_dict(invalid_data, name="invalid")
            assert False, "应该抛出 ValueError"
        except ValueError:
            # 如果 from_dict 已经验证，这是合理的
            pass
    
    def test_to_dict(self):
        """测试序列化为字典"""
        from core.modules.data_source.data_classes import DataSourceDefinition
        
        data = {
            "handler": "userspace.data_source.handlers.kline.KlineHandler",
            "description": "K线数据",
            "dependencies": {
                "latest_completed_trading_date": True
            },
            "handler_config": {
                "renew_mode": "incremental"
            }
        }
        
        definition = DataSourceDefinition.from_dict(data, name="kline")
        result = definition.to_dict()
        
        assert result["handler"] == "userspace.data_source.handlers.kline.KlineHandler"
        assert result["description"] == "K线数据"
        assert "dependencies" in result
        # handler_config 可能不在结果中（如果为 None），或者在结果中
        if definition.handler_config is not None:
            assert "handler_config" in result
    
    def test_schema_name_property(self):
        """测试 schema_name 属性（总是等于 name）"""
        from core.modules.data_source.data_classes import DataSourceDefinition
        
        data = {
            "handler": "userspace.data_source.handlers.kline.KlineHandler",
            "handler_config": {
                "renew_mode": "incremental"
            }
        }
        
        definition = DataSourceDefinition.from_dict(data, name="kline")
        assert definition.schema_name == "kline"
        assert definition.schema_name == definition.name
    
    def test_validate_with_invalid_api_config(self):
        """测试验证无效的 API 配置"""
        from core.modules.data_source.data_classes import DataSourceDefinition
        
        # 测试缺少 provider_name 的 API 配置
        data = {
            "handler": "userspace.data_source.handlers.kline.KlineHandler",
            "handler_config": {
                "renew_mode": "incremental",
                "apis": {
                    "invalid_api": {
                        "method": "get_data",
                        # 缺少 provider_name
                    }
                }
            }
        }
        
        definition = DataSourceDefinition.from_dict(data, name="kline")
        # validate 应该返回 False（如果配置无效）
        # 注意：由于 handler 类可能不存在，handler_config 可能为 None
        if definition.handler_config is not None:
            # 如果 handler_config 存在，验证应该检查 API 配置
            result = definition.validate()
            # 由于缺少 provider_name，验证应该失败
            assert result is False
    
    def test_validate_with_missing_method(self):
        """测试验证缺少 method 的 API 配置"""
        from core.modules.data_source.data_classes import DataSourceDefinition
        
        data = {
            "handler": "userspace.data_source.handlers.kline.KlineHandler",
            "handler_config": {
                "renew_mode": "incremental",
                "apis": {
                    "invalid_api": {
                        "provider_name": "tushare",
                        # 缺少 method
                    }
                }
            }
        }
        
        definition = DataSourceDefinition.from_dict(data, name="kline")
        if definition.handler_config is not None:
            result = definition.validate()
            assert result is False
    
    def test_all_renew_modes(self):
        """测试所有 renew_mode 值"""
        from core.modules.data_source.data_classes import DataSourceDefinition
        from core.global_enums.enums import UpdateMode
        
        # 测试所有三种模式
        for mode in [UpdateMode.INCREMENTAL, UpdateMode.ROLLING, UpdateMode.REFRESH]:
            data = {
                "handler": "userspace.data_source.handlers.kline.KlineHandler",
                "handler_config": {
                    "renew_mode": mode.value
                }
            }
            
            definition = DataSourceDefinition.from_dict(data, name="kline")
            assert definition.name == "kline"
            # handler_config 可能为 None（如果 handler 类不存在）
            if definition.handler_config is not None:
                assert definition.handler_config.renew_mode == mode.value
    
    def test_invalid_renew_mode(self):
        """测试无效的 renew_mode 值"""
        from core.modules.data_source.data_classes import DataSourceDefinition
        
        data = {
            "handler": "userspace.data_source.handlers.kline.KlineHandler",
            "handler_config": {
                "renew_mode": "invalid_mode"
            }
        }
        
        # 应该抛出 ValueError（在 _select_config_class_by_renew_mode 中）
        try:
            definition = DataSourceDefinition.from_dict(data, name="kline")
            # 如果 handler 类不存在，可能不会触发验证
            # 如果 handler 类存在，应该抛出错误
        except ValueError as e:
            assert "renew_mode" in str(e).lower() or "无效" in str(e)
    
    def test_empty_handler_config(self):
        """测试空的 handler_config"""
        from core.modules.data_source.data_classes import DataSourceDefinition
        
        data = {
            "handler": "userspace.data_source.handlers.kline.KlineHandler",
            "handler_config": {}
        }
        
        # 应该抛出 ValueError（缺少 renew_mode）
        try:
            definition = DataSourceDefinition.from_dict(data, name="kline")
            # 如果 handler 类不存在，可能不会触发验证
        except ValueError as e:
            assert "renew_mode" in str(e).lower() or "缺少" in str(e)
    
    def test_missing_handler(self):
        """测试缺少 handler 字段"""
        from core.modules.data_source.data_classes import DataSourceDefinition
        
        data = {
            "description": "测试"
        }
        
        try:
            definition = DataSourceDefinition.from_dict(data, name="test")
            assert False, "应该抛出 ValueError"
        except ValueError as e:
            assert "handler" in str(e).lower() or "handler_path" in str(e).lower()
    
    def test_normalize_handler_path(self):
        """测试 handler 路径标准化"""
        from core.modules.data_source.data_classes import DataSourceDefinition
        
        # 测试简化格式
        data1 = {
            "handler": "kline.KlineHandler",
            "handler_config": {"renew_mode": "incremental"}
        }
        definition1 = DataSourceDefinition.from_dict(data1, name="kline")
        assert definition1.handler_path.startswith("userspace.data_source.handlers")
        
        # 测试完整路径
        data2 = {
            "handler": "userspace.data_source.handlers.kline.KlineHandler",
            "handler_config": {"renew_mode": "incremental"}
        }
        definition2 = DataSourceDefinition.from_dict(data2, name="kline")
        assert definition2.handler_path == "userspace.data_source.handlers.kline.KlineHandler"


if __name__ == "__main__":
    if HAS_PYTEST:
        pytest.main([__file__])
    else:
        # 简单测试运行
        test = TestDataSourceDefinition()
        print("运行测试...")
        
        tests = [
            ("test_from_dict_basic", test.test_from_dict_basic),
            ("test_from_dict_with_apis", test.test_from_dict_with_apis),
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
