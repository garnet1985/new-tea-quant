"""
OpportunityEnumeratorSettings 单元测试
"""
import sys
from pathlib import Path
from unittest.mock import patch

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False

from core.modules.strategy.components.opportunity_enumerator.enumerator_settings import (
    OpportunityEnumeratorSettings
)
from core.modules.strategy.models.strategy_settings import StrategySettings


class TestOpportunityEnumeratorSettings:
    """OpportunityEnumeratorSettings 测试类"""
    
    def test_from_raw_basic(self):
        """测试从原始 settings 创建（基本配置）"""
        settings_dict = {
            "name": "test_strategy",
            "data": {
                "base_price_source": "stock_kline_daily",
                "adjust_type": "qfq",
                "min_required_records": 200
            },
            "goal": {
                "expiration": {"fixed_window_in_days": 30}
            }
        }
        
        enum_settings = OpportunityEnumeratorSettings.from_raw(
            strategy_name="test_strategy",
            settings_dict=settings_dict
        )
        
        assert enum_settings.strategy_name == "test_strategy"
        assert enum_settings.data["base_price_source"] == "stock_kline_daily"
        assert enum_settings.data["adjust_type"] == "qfq"
        assert enum_settings.min_required_records == 200
        assert enum_settings.goal == settings_dict["goal"]
    
    def test_from_raw_missing_base_price_source(self):
        """测试从原始 settings 创建（缺少 base_price_source）"""
        settings_dict = {
            "name": "test_strategy",
            "data": {
                "adjust_type": "qfq"
            },
            "goal": {}
        }
        
        with pytest.raises(ValueError, match="base_price_source"):
            OpportunityEnumeratorSettings.from_raw(
                strategy_name="test_strategy",
                settings_dict=settings_dict
            )
    
    def test_from_raw_missing_adjust_type(self):
        """测试从原始 settings 创建（缺少 adjust_type）"""
        settings_dict = {
            "name": "test_strategy",
            "data": {
                "base_price_source": "stock_kline_daily"
            },
            "goal": {}
        }
        
        with pytest.raises(ValueError, match="adjust_type"):
            OpportunityEnumeratorSettings.from_raw(
                strategy_name="test_strategy",
                settings_dict=settings_dict
            )
    
    def test_from_raw_missing_goal(self):
        """测试从原始 settings 创建（缺少 goal）"""
        settings_dict = {
            "name": "test_strategy",
            "data": {
                "base_price_source": "stock_kline_daily",
                "adjust_type": "qfq"
            }
        }
        
        with pytest.raises(ValueError, match="goal"):
            OpportunityEnumeratorSettings.from_raw(
                strategy_name="test_strategy",
                settings_dict=settings_dict
            )
    
    def test_from_raw_default_min_required_records(self):
        """测试从原始 settings 创建（使用默认 min_required_records）"""
        settings_dict = {
            "name": "test_strategy",
            "data": {
                "base_price_source": "stock_kline_daily",
                "adjust_type": "qfq"
            },
            "goal": {
                "expiration": {"fixed_window_in_days": 30}
            }
        }
        
        enum_settings = OpportunityEnumeratorSettings.from_raw(
            strategy_name="test_strategy",
            settings_dict=settings_dict
        )
        
        assert enum_settings.min_required_records == 100  # 默认值
    
    def test_from_raw_default_indicators(self):
        """测试从原始 settings 创建（使用默认 indicators）"""
        settings_dict = {
            "name": "test_strategy",
            "data": {
                "base_price_source": "stock_kline_daily",
                "adjust_type": "qfq"
            },
            "goal": {
                "expiration": {"fixed_window_in_days": 30}
            }
        }
        
        enum_settings = OpportunityEnumeratorSettings.from_raw(
            strategy_name="test_strategy",
            settings_dict=settings_dict
        )
        
        assert enum_settings.data["indicators"] == {}  # 默认空字典
    
    def test_from_raw_use_sampling_default(self):
        """测试从原始 settings 创建（use_sampling 默认值）"""
        settings_dict = {
            "name": "test_strategy",
            "data": {
                "base_price_source": "stock_kline_daily",
                "adjust_type": "qfq"
            },
            "goal": {
                "expiration": {"fixed_window_in_days": 30}
            }
        }
        
        enum_settings = OpportunityEnumeratorSettings.from_raw(
            strategy_name="test_strategy",
            settings_dict=settings_dict
        )
        
        assert enum_settings.use_sampling is True  # 默认 True
    
    def test_from_raw_use_sampling_explicit(self):
        """测试从原始 settings 创建（use_sampling 显式设置）"""
        settings_dict = {
            "name": "test_strategy",
            "data": {
                "base_price_source": "stock_kline_daily",
                "adjust_type": "qfq"
            },
            "enumerator": {
                "use_sampling": False
            },
            "goal": {
                "expiration": {"fixed_window_in_days": 30}
            }
        }
        
        enum_settings = OpportunityEnumeratorSettings.from_raw(
            strategy_name="test_strategy",
            settings_dict=settings_dict
        )
        
        assert enum_settings.use_sampling is False
    
    def test_from_base_settings(self):
        """测试从 StrategySettings 创建"""
        settings_dict = {
            "name": "test_strategy",
            "data": {
                "base_price_source": "stock_kline_daily",
                "adjust_type": "qfq"
            },
            "goal": {
                "expiration": {"fixed_window_in_days": 30}
            }
        }
        
        base_settings = StrategySettings.from_dict(settings_dict)
        enum_settings = OpportunityEnumeratorSettings.from_base(base_settings)
        
        assert enum_settings.strategy_name == "test_strategy"
        assert enum_settings.data["base_price_source"] == "stock_kline_daily"
    
    def test_to_dict(self):
        """测试导出为字典"""
        settings_dict = {
            "name": "test_strategy",
            "core": {"rsi_threshold": 20},
            "data": {
                "base_price_source": "stock_kline_daily",
                "adjust_type": "qfq"
            },
            "goal": {
                "expiration": {"fixed_window_in_days": 30}
            }
        }
        
        enum_settings = OpportunityEnumeratorSettings.from_raw(
            strategy_name="test_strategy",
            settings_dict=settings_dict
        )
        
        result = enum_settings.to_dict()
        
        assert result["core"] == {"rsi_threshold": 20}  # 保留原始字段
        assert result["data"]["base_price_source"] == "stock_kline_daily"
        assert result["enumerator"]["use_sampling"] is True
        assert result["enumerator"]["max_test_versions"] == 10  # 默认值
    
    def test_max_test_versions_default(self):
        """测试 max_test_versions 默认值"""
        settings_dict = {
            "name": "test_strategy",
            "data": {
                "base_price_source": "stock_kline_daily",
                "adjust_type": "qfq"
            },
            "goal": {
                "expiration": {"fixed_window_in_days": 30}
            }
        }
        
        enum_settings = OpportunityEnumeratorSettings.from_raw(
            strategy_name="test_strategy",
            settings_dict=settings_dict
        )
        
        assert enum_settings.max_test_versions == 10
    
    def test_max_output_versions_default(self):
        """测试 max_output_versions 默认值"""
        settings_dict = {
            "name": "test_strategy",
            "data": {
                "base_price_source": "stock_kline_daily",
                "adjust_type": "qfq"
            },
            "goal": {
                "expiration": {"fixed_window_in_days": 30}
            }
        }
        
        enum_settings = OpportunityEnumeratorSettings.from_raw(
            strategy_name="test_strategy",
            settings_dict=settings_dict
        )
        
        assert enum_settings.max_output_versions == 3
    
    def test_max_workers_default(self):
        """测试 max_workers 默认值"""
        settings_dict = {
            "name": "test_strategy",
            "data": {
                "base_price_source": "stock_kline_daily",
                "adjust_type": "qfq"
            },
            "goal": {
                "expiration": {"fixed_window_in_days": 30}
            }
        }
        
        enum_settings = OpportunityEnumeratorSettings.from_raw(
            strategy_name="test_strategy",
            settings_dict=settings_dict
        )
        
        assert enum_settings.max_workers == "auto"
