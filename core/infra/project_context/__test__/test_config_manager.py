"""
ConfigManager 单元测试
"""
import pytest
import json
import tempfile
from pathlib import Path
from core.infra.project_context.config_manager import ConfigManager


class TestConfigManager:
    """ConfigManager 测试类"""
    
    def test_load_json_existing(self):
        """测试加载存在的 JSON 文件"""
        # 使用项目中的实际配置文件
        root = PathManager.get_root()
        core_config = root / "core" / "config" / "data.json"
        
        if core_config.exists():
            config = ConfigManager.load_json(core_config)
            assert isinstance(config, dict)
            assert len(config) > 0
    
    def test_load_json_nonexistent(self):
        """测试加载不存在的 JSON 文件"""
        nonexistent = Path("/nonexistent/path/config.json")
        config = ConfigManager.load_json(nonexistent)
        
        # 应该返回空字典
        assert config == {}
    
    def test_load_core_config(self):
        """测试加载核心配置"""
        # 测试加载 data 配置
        data_config = ConfigManager.load_data_config()
        
        assert isinstance(data_config, dict)
        assert "default_start_date" in data_config
        assert "decimal_places" in data_config
    
    def test_get_default_start_date(self):
        """测试获取默认开始日期"""
        start_date = ConfigManager.get_default_start_date()
        
        assert isinstance(start_date, str)
        assert len(start_date) == 8  # YYYYMMDD 格式
        assert start_date.isdigit()
    
    def test_get_decimal_places(self):
        """测试获取小数位数"""
        decimal_places = ConfigManager.get_decimal_places()
        
        assert isinstance(decimal_places, int)
        assert decimal_places >= 0

    def test_get_adj_factor_event_decimal_places(self):
        places = ConfigManager.get_adj_factor_event_decimal_places()
        assert places["factor_places"] == 4
        assert places["price_places"] == 3
        assert places["diff_places"] == 4

    def test_deep_merge_decimal_places_nested(self):
        merged = ConfigManager._deep_merge_config(
            {
                "decimal_places": {
                    "default": 2,
                    "adj_factor_event": {
                        "factor_places": 4,
                        "price_places": 3,
                        "diff_places": 4,
                    },
                }
            },
            {
                "decimal_places": {
                    "default": 3,
                    "adj_factor_event": {"factor_places": 5},
                }
            },
            deep_merge_fields={"decimal_places"},
        )
        dp = merged["decimal_places"]
        assert dp["default"] == 3
        assert dp["adj_factor_event"]["factor_places"] == 5
        assert dp["adj_factor_event"]["price_places"] == 3
        assert dp["adj_factor_event"]["diff_places"] == 4
    
    def test_get_database_config(self):
        """测试获取数据库配置"""
        db_config = ConfigManager.load_database_config()

        assert isinstance(db_config, dict)
        assert "database_type" in db_config
        assert db_config["database_type"] in ("postgresql", "mysql", "duckdb")

    def test_get_database_type(self):
        """测试获取数据库类型"""
        db_type = ConfigManager.get_database_type()

        assert isinstance(db_type, str)
        assert db_type in ("postgresql", "mysql", "duckdb")
    
    def test_load_with_defaults(self):
        """测试加载配置（默认+用户）"""
        # 创建临时配置文件
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            # 创建默认配置
            default_config = tmp_path / "default.json"
            default_config.write_text(json.dumps({"key1": "default", "key2": "default"}))
            
            # 创建用户配置
            user_config = tmp_path / "user.json"
            user_config.write_text(json.dumps({"key1": "user"}))
            
            # 测试加载
            merged = ConfigManager.load_with_defaults(
                default_config,
                user_config,
                deep_merge_fields=set(),
                override_fields=set()
            )
            
            assert merged["key1"] == "user"  # 用户配置覆盖
            assert merged["key2"] == "default"  # 默认配置保留


# 导入 PathManager 用于测试
from core.infra.project_context.path_manager import PathManager
