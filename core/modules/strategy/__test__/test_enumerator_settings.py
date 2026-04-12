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
from core.modules.data_contract.contract_const import DataKey
from core.modules.strategy.models.strategy_settings import StrategySettings


def _data_block(**extra):
    d = {
        "base_required_data": {
            "params": {"term": "daily"},
        },
    }
    d.update(extra)
    return d


class TestOpportunityEnumeratorSettings:
    """OpportunityEnumeratorSettings 测试类"""
    
    def test_from_raw_basic(self):
        """测试从原始 settings 创建（基本配置）"""
        settings_dict = {
            "name": "test_strategy",
            "data": _data_block(min_required_records=200),
            "goal": {
                "expiration": {"fixed_window_in_days": 30}
            }
        }
        
        enum_settings = OpportunityEnumeratorSettings.from_raw(
            strategy_name="test_strategy",
            settings_dict=settings_dict
        )
        
        assert enum_settings.strategy_name == "test_strategy"
        assert enum_settings.data["base_required_data"]["params"]["term"] == "daily"
        assert enum_settings.min_required_records == 200
        assert enum_settings.goal == settings_dict["goal"]
    
    def test_from_raw_missing_base_required_data(self):
        """测试从原始 settings 创建（缺少 base_required_data）"""
        settings_dict = {
            "name": "test_strategy",
            "data": {},
            "goal": {}
        }
        
        with pytest.raises(ValueError, match="base_required_data"):
            OpportunityEnumeratorSettings.from_raw(
                strategy_name="test_strategy",
                settings_dict=settings_dict
            )
    
    def test_from_raw_missing_goal(self):
        """测试从原始 settings 创建（缺少 goal）"""
        settings_dict = {
            "name": "test_strategy",
            "data": _data_block(),
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
            "data": _data_block(),
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
            "data": _data_block(),
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
            "data": _data_block(),
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
            "data": _data_block(),
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
            "data": _data_block(),
            "goal": {
                "expiration": {"fixed_window_in_days": 30}
            }
        }
        
        base_settings = StrategySettings.from_dict(settings_dict)
        enum_settings = OpportunityEnumeratorSettings.from_base(base_settings)
        
        assert enum_settings.strategy_name == "test_strategy"
        assert enum_settings.data["base_required_data"]["params"]["term"] == "daily"
    
    def test_to_dict(self):
        """测试导出为字典"""
        settings_dict = {
            "name": "test_strategy",
            "core": {"rsi_threshold": 20},
            "data": _data_block(),
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
        assert result["data"]["base_required_data"]["params"]["term"] == "daily"
        assert result["enumerator"]["use_sampling"] is True
        assert result["enumerator"]["max_test_versions"] == 10  # 默认值
    
    def test_max_test_versions_default(self):
        """测试 max_test_versions 默认值"""
        settings_dict = {
            "name": "test_strategy",
            "data": _data_block(),
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
            "data": _data_block(),
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
            "data": _data_block(),
            "goal": {
                "expiration": {"fixed_window_in_days": 30}
            }
        }
        
        enum_settings = OpportunityEnumeratorSettings.from_raw(
            strategy_name="test_strategy",
            settings_dict=settings_dict
        )
        
        assert enum_settings.max_workers == "auto"

    def test_base_rejects_granular_kline_data_id(self):
        """主依赖不允许使用 stock.kline.daily.qfq 等细粒度 data_id"""
        settings_dict = {
            "name": "test_strategy",
            "data": {
                "base_required_data": {
                    "data_id": DataKey.STOCK_KLINE_DAILY_QFQ.value,
                    "params": {"term": "daily"},
                },
            },
            "goal": {"expiration": {"fixed_window_in_days": 30}},
        }
        with pytest.raises(ValueError, match="只能为"):
            OpportunityEnumeratorSettings.from_raw("test_strategy", settings_dict)

    def test_base_requires_term(self):
        """params.term 必填"""
        settings_dict = {
            "name": "test_strategy",
            "data": {
                "base_required_data": {
                    "params": {"adjust": "qfq"},
                },
            },
            "goal": {"expiration": {"fixed_window_in_days": 30}},
        }
        with pytest.raises(ValueError, match="term"):
            OpportunityEnumeratorSettings.from_raw("test_strategy", settings_dict)

    def test_resolved_adjust_defaults_qfq(self):
        ss = StrategySettings.from_dict(
            {
                "name": "t",
                "data": {"base_required_data": {"params": {"term": "daily"}}},
            }
        )
        assert ss.adjust_type == "qfq"
        assert ss.resolved_base_required_data["data_id"] == DataKey.STOCK_KLINE.value
