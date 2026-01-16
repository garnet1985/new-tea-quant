"""
util.py 单元测试
"""
try:
    import pytest
except ImportError:
    pytest = None

from core.utils.util import deep_merge_config, merge_mapping_configs


class TestDeepMergeConfig:
    """deep_merge_config 测试类"""
    
    def test_simple_override(self):
        """测试简单覆盖"""
        defaults = {"a": 1, "b": 2}
        custom = {"b": 3}
        result = deep_merge_config(defaults, custom)
        assert result["a"] == 1
        assert result["b"] == 3
    
    def test_deep_merge(self):
        """测试深度合并"""
        defaults = {"params": {"a": 1, "b": 2}}
        custom = {"params": {"b": 3, "c": 4}}
        result = deep_merge_config(
            defaults, 
            custom, 
            deep_merge_fields={"params"}
        )
        assert result["params"]["a"] == 1  # 保留 defaults
        assert result["params"]["b"] == 3  # custom 覆盖
        assert result["params"]["c"] == 4  # custom 新增
    
    def test_override_fields(self):
        """测试完全覆盖字段"""
        defaults = {"dependencies": {"dep1": True, "dep2": False}}
        custom = {"dependencies": {"dep1": False}}
        result = deep_merge_config(
            defaults,
            custom,
            override_fields={"dependencies"}
        )
        assert result["dependencies"] == {"dep1": False}  # 完全覆盖
    
    def test_mixed_fields(self):
        """测试混合字段"""
        defaults = {
            "handler": "default.handler",
            "params": {"a": 1, "b": 2},
            "dependencies": {"dep1": True}
        }
        custom = {
            "params": {"b": 3, "c": 4},
            "dependencies": {"dep2": True}
        }
        result = deep_merge_config(
            defaults,
            custom,
            deep_merge_fields={"params"},
            override_fields={"dependencies"}
        )
        assert result["handler"] == "default.handler"
        assert result["params"] == {"a": 1, "b": 3, "c": 4}  # 深度合并
        assert result["dependencies"] == {"dep2": True}  # 完全覆盖


class TestMergeMappingConfigs:
    """merge_mapping_configs 测试类"""
    
    def test_simple_merge(self):
        """测试简单合并"""
        defaults = {
            "kline": {"handler": "default.handler", "params": {"a": 1}}
        }
        custom = {
            "kline": {"params": {"b": 2}}
        }
        result = merge_mapping_configs(
            defaults,
            custom,
            deep_merge_fields={"params"}
        )
        assert result["kline"]["handler"] == "default.handler"
        assert result["kline"]["params"] == {"a": 1, "b": 2}
    
    def test_new_data_source(self):
        """测试新增 data_source"""
        defaults = {"kline": {"handler": "kline.handler"}}
        custom = {"new_source": {"handler": "new.handler"}}
        result = merge_mapping_configs(defaults, custom)
        assert "new_source" in result
        assert result["new_source"]["handler"] == "new.handler"
    
    def test_multiple_sources(self):
        """测试多个 data_source"""
        defaults = {
            "kline": {"handler": "kline.handler", "params": {"a": 1}},
            "finance": {"handler": "finance.handler"}
        }
        custom = {
            "kline": {"params": {"b": 2}},
            "finance": {"params": {"c": 3}}
        }
        result = merge_mapping_configs(
            defaults,
            custom,
            deep_merge_fields={"params"}
        )
        assert result["kline"]["params"] == {"a": 1, "b": 2}
        assert result["finance"]["params"] == {"c": 3}
