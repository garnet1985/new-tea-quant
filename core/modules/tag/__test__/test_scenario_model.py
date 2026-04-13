"""
ScenarioModel 单元测试
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


class TestScenarioModel:
    """ScenarioModel 测试类"""
    
    def test_create_from_settings_basic(self):
        """测试从 settings 创建 ScenarioModel（基本配置）"""
        from core.modules.tag.core.models.scenario_model import ScenarioModel
        
        settings = {
            "name": "test_scenario",
            "target_entity": {"type": "stock_kline_daily"},
            "is_enabled": True,
            "data": {"required": [{"data_id": "stock.kline", "params": {"term": "daily", "adjust": "qfq"}}]},
            "tags": [
                {"name": "tag1", "display_name": "Tag 1"},
                {"name": "tag2", "display_name": "Tag 2"}
            ],
            "incremental_required_records_before_as_of_date": 10
        }
        
        scenario = ScenarioModel.create_from_settings(settings)
        
        assert scenario is not None
        assert scenario.name == "test_scenario"
        assert scenario.get_target_entity() == "stock_kline_daily"
        assert scenario.is_enabled() is True
        assert len(scenario.get_tag_models()) == 2
        assert scenario.get_tag_models()[0].get_name() == "tag1"
        assert scenario.get_tag_models()[1].get_name() == "tag2"
    
    def test_create_from_settings_with_display_name(self):
        """测试从 settings 创建 ScenarioModel（带 display_name）"""
        from core.modules.tag.core.models.scenario_model import ScenarioModel
        
        settings = {
            "name": "test_scenario",
            "display_name": "Test Scenario Display",
            "description": "Test description",
            "target_entity": {"type": "stock_kline_daily"},
            "is_enabled": True,
            "data": {"required": [{"data_id": "stock.kline", "params": {"term": "daily", "adjust": "qfq"}}]},
            "tags": [
                {"name": "tag1"}
            ],
            "incremental_required_records_before_as_of_date": 10
        }
        
        scenario = ScenarioModel.create_from_settings(settings)
        
        assert scenario is not None
        assert scenario.display_name == "Test Scenario Display"
        assert scenario.description == "Test description"
    
    def test_create_from_settings_default_display_name(self):
        """测试从 settings 创建 ScenarioModel（默认 display_name）"""
        from core.modules.tag.core.models.scenario_model import ScenarioModel
        
        settings = {
            "name": "test_scenario",
            "target_entity": {"type": "stock_kline_daily"},
            "is_enabled": True,
            "data": {"required": [{"data_id": "stock.kline", "params": {"term": "daily", "adjust": "qfq"}}]},
            "tags": [
                {"name": "tag1"}
            ],
            "incremental_required_records_before_as_of_date": 10
        }
        
        scenario = ScenarioModel.create_from_settings(settings)
        
        assert scenario is not None
        assert scenario.display_name == "test_scenario"  # 应该使用 name 作为默认值
    
    def test_create_from_settings_target_entity_string_invalid(self):
        """测试从 settings 创建 ScenarioModel（target_entity 字符串已不支持）"""
        from core.modules.tag.core.models.scenario_model import ScenarioModel
        
        settings = {
            "name": "test_scenario",
            "target_entity": "stock_kline_daily",  # 非法：必须是 dict
            "is_enabled": True,
            "data": {"required": [{"data_id": "stock.kline", "params": {"term": "daily", "adjust": "qfq"}}]},
            "tags": [
                {"name": "tag1"}
            ],
            "incremental_required_records_before_as_of_date": 10
        }
        
        scenario = ScenarioModel.create_from_settings(settings)
        assert scenario is None
    
    def test_is_setting_valid_valid(self):
        """测试 is_setting_valid（有效配置）"""
        from core.modules.tag.core.models.scenario_model import ScenarioModel
        
        settings = {
            "name": "test_scenario",
            "target_entity": {"type": "stock_kline_daily"},
            "is_enabled": True,
            "data": {"required": [{"data_id": "stock.kline", "params": {"term": "daily", "adjust": "qfq"}}]},
            "tags": [
                {"name": "tag1"}
            ],
            "incremental_required_records_before_as_of_date": 10
        }
        
        assert ScenarioModel.is_setting_valid(settings) is True
    
    def test_is_setting_valid_missing_target_entity(self):
        """测试 is_setting_valid（缺少 target_entity）"""
        from core.modules.tag.core.models.scenario_model import ScenarioModel
        
        settings = {
            "name": "test_scenario",
            "is_enabled": True,
            "data": {"required": [{"data_id": "stock.kline", "params": {"term": "daily", "adjust": "qfq"}}]},
            "tags": [
                {"name": "tag1"}
            ]
        }
        
        assert ScenarioModel.is_setting_valid(settings) is False
    
    def test_is_setting_valid_missing_tags(self):
        """测试 is_setting_valid（缺少 tags）"""
        from core.modules.tag.core.models.scenario_model import ScenarioModel
        
        settings = {
            "name": "test_scenario",
            "target_entity": {"type": "stock_kline_daily"},
            "is_enabled": True
        }
        
        assert ScenarioModel.is_setting_valid(settings) is False
    
    def test_is_setting_valid_empty_tags(self):
        """测试 is_setting_valid（tags 为空列表）"""
        from core.modules.tag.core.models.scenario_model import ScenarioModel
        
        settings = {
            "name": "test_scenario",
            "target_entity": {"type": "stock_kline_daily"},
            "is_enabled": True,
            "data": {"required": [{"data_id": "stock.kline", "params": {"term": "daily", "adjust": "qfq"}}]},
            "tags": []
        }
        
        assert ScenarioModel.is_setting_valid(settings) is False
    
    def test_is_setting_valid_incremental_missing_required_records(self):
        """测试 is_setting_valid（INCREMENTAL 模式缺少 required_records）"""
        from core.modules.tag.core.models.scenario_model import ScenarioModel
        
        settings = {
            "name": "test_scenario",
            "target_entity": {"type": "stock_kline_daily"},
            "is_enabled": True,
            "data": {"required": [{"data_id": "stock.kline", "params": {"term": "daily", "adjust": "qfq"}}]},
            "tags": [
                {"name": "tag1"}
            ],
            "update_mode": "incremental"
            # 缺少 incremental_required_records_before_as_of_date
        }
        
        assert ScenarioModel.is_setting_valid(settings) is False
    
    def test_is_setting_valid_incremental_invalid_required_records(self):
        """测试 is_setting_valid（INCREMENTAL 模式 required_records 无效）"""
        from core.modules.tag.core.models.scenario_model import ScenarioModel
        
        settings = {
            "name": "test_scenario",
            "target_entity": {"type": "stock_kline_daily"},
            "is_enabled": True,
            "data": {"required": [{"data_id": "stock.kline", "params": {"term": "daily", "adjust": "qfq"}}]},
            "tags": [
                {"name": "tag1"}
            ],
            "update_mode": "incremental",
            "incremental_required_records_before_as_of_date": -1  # 负数无效
        }
        
        assert ScenarioModel.is_setting_valid(settings) is False
    
    def test_calculate_update_mode_incremental(self):
        """测试 calculate_update_mode（INCREMENTAL 模式）"""
        from core.modules.tag.core.models.scenario_model import ScenarioModel
        from core.modules.tag.core.enums import TagUpdateMode
        
        settings = {
            "name": "test_scenario",
            "target_entity": {"type": "stock_kline_daily"},
            "is_enabled": True,
            "data": {"required": [{"data_id": "stock.kline", "params": {"term": "daily", "adjust": "qfq"}}]},
            "tags": [
                {"name": "tag1"}
            ],
            "update_mode": "incremental",
            "incremental_required_records_before_as_of_date": 10
        }
        
        scenario = ScenarioModel.create_from_settings(settings)
        assert scenario.calculate_update_mode() == TagUpdateMode.INCREMENTAL
    
    def test_calculate_update_mode_refresh(self):
        """测试 calculate_update_mode（REFRESH 模式）"""
        from core.modules.tag.core.models.scenario_model import ScenarioModel
        from core.modules.tag.core.enums import TagUpdateMode
        
        settings = {
            "name": "test_scenario",
            "target_entity": {"type": "stock_kline_daily"},
            "is_enabled": True,
            "data": {"required": [{"data_id": "stock.kline", "params": {"term": "daily", "adjust": "qfq"}}]},
            "tags": [
                {"name": "tag1"}
            ],
            "update_mode": "refresh",
            "incremental_required_records_before_as_of_date": 10
        }
        
        scenario = ScenarioModel.create_from_settings(settings)
        assert scenario.calculate_update_mode() == TagUpdateMode.REFRESH
    
    def test_calculate_update_mode_recompute(self):
        """测试 calculate_update_mode（recompute=True 时返回 REFRESH）"""
        from core.modules.tag.core.models.scenario_model import ScenarioModel
        from core.modules.tag.core.enums import TagUpdateMode
        
        settings = {
            "name": "test_scenario",
            "target_entity": {"type": "stock_kline_daily"},
            "is_enabled": True,
            "data": {"required": [{"data_id": "stock.kline", "params": {"term": "daily", "adjust": "qfq"}}]},
            "tags": [
                {"name": "tag1"}
            ],
            "recompute": True,
            "incremental_required_records_before_as_of_date": 10
        }
        
        scenario = ScenarioModel.create_from_settings(settings)
        assert scenario.should_recompute() is True
        assert scenario.calculate_update_mode() == TagUpdateMode.REFRESH
    
    def test_calculate_update_mode_default(self):
        """测试 calculate_update_mode（默认值）"""
        from core.modules.tag.core.models.scenario_model import ScenarioModel
        from core.modules.tag.core.enums import TagUpdateMode
        
        settings = {
            "name": "test_scenario",
            "target_entity": {"type": "stock_kline_daily"},
            "is_enabled": True,
            "data": {"required": [{"data_id": "stock.kline", "params": {"term": "daily", "adjust": "qfq"}}]},
            "tags": [
                {"name": "tag1"}
            ],
            "incremental_required_records_before_as_of_date": 10
        }
        
        scenario = ScenarioModel.create_from_settings(settings)
        # 默认应该是 INCREMENTAL
        assert scenario.calculate_update_mode() == TagUpdateMode.INCREMENTAL
    
    def test_get_tags_dict(self):
        """测试 get_tags_dict"""
        from core.modules.tag.core.models.scenario_model import ScenarioModel
        
        settings = {
            "name": "test_scenario",
            "target_entity": {"type": "stock_kline_daily"},
            "is_enabled": True,
            "data": {"required": [{"data_id": "stock.kline", "params": {"term": "daily", "adjust": "qfq"}}]},
            "tags": [
                {"name": "tag1", "display_name": "Tag 1"},
                {"name": "tag2", "display_name": "Tag 2"}
            ],
            "incremental_required_records_before_as_of_date": 10
        }
        
        scenario = ScenarioModel.create_from_settings(settings)
        tags_dict = scenario.get_tags_dict()
        
        assert "tag1" in tags_dict
        assert "tag2" in tags_dict
        assert tags_dict["tag1"]["tag_name"] == "tag1"
        assert tags_dict["tag2"]["tag_name"] == "tag2"
    
    def test_to_dict(self):
        """测试 to_dict"""
        from core.modules.tag.core.models.scenario_model import ScenarioModel
        
        settings = {
            "name": "test_scenario",
            "display_name": "Test Scenario",
            "description": "Test description",
            "target_entity": {"type": "stock_kline_daily"},
            "is_enabled": True,
            "data": {"required": [{"data_id": "stock.kline", "params": {"term": "daily", "adjust": "qfq"}}]},
            "tags": [
                {"name": "tag1"}
            ],
            "incremental_required_records_before_as_of_date": 10
        }
        
        scenario = ScenarioModel.create_from_settings(settings)
        scenario.id = 1
        scenario.created_at = "2024-01-01"
        scenario.updated_at = "2024-01-02"
        
        result = scenario.to_dict()
        
        assert result["id"] == 1
        assert result["name"] == "test_scenario"
        assert result["display_name"] == "Test Scenario"
        assert result["description"] == "Test description"
        assert result["created_at"] == "2024-01-01"
        assert result["updated_at"] == "2024-01-02"

    def test_is_setting_valid_general_requires_axis(self):
        """测试 general 模式必须声明 tag_time_axis_based_on"""
        from core.modules.tag.core.models.scenario_model import ScenarioModel

        settings = {
            "name": "macro_general",
            "tag_target_type": "general",
            "is_enabled": True,
            "data": {
                "required": [
                    {"data_id": "macro.gdp", "params": {}},
                ],
            },
            "tags": [{"name": "macro_tag"}],
            "incremental_required_records_before_as_of_date": 0,
        }

        assert ScenarioModel.is_setting_valid(settings) is False

    def test_is_setting_valid_general_with_axis(self):
        """测试 general 模式合法配置"""
        from core.modules.tag.core.models.scenario_model import ScenarioModel

        settings = {
            "name": "macro_general",
            "tag_target_type": "general",
            "is_enabled": True,
            "data": {
                "required": [
                    {"data_id": "macro.gdp", "params": {}},
                ],
                "tag_time_axis_based_on": "macro.gdp",
            },
            "tags": [{"name": "macro_tag"}],
            "incremental_required_records_before_as_of_date": 0,
        }

        assert ScenarioModel.is_setting_valid(settings) is True
