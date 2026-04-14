"""
TagModel 单元测试
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


class TestTagModel:
    """TagModel 测试类"""
    
    def test_create_from_settings_basic(self):
        """测试从 settings 创建 TagModel（基本配置）"""
        from core.modules.tag.models.tag_model import TagModel
        
        tag_setting = {
            "name": "test_tag"
        }
        
        tag = TagModel.create_from_settings(tag_setting)
        
        assert tag is not None
        assert tag.get_name() == "test_tag"
        assert tag.tag_name == "test_tag"
        assert tag.display_name == "test_tag"  # 默认使用 name
        assert tag.description == ""  # 默认空字符串
    
    def test_create_from_settings_with_display_name(self):
        """测试从 settings 创建 TagModel（带 display_name）"""
        from core.modules.tag.models.tag_model import TagModel
        
        tag_setting = {
            "name": "test_tag",
            "display_name": "Test Tag Display",
            "description": "Test description"
        }
        
        tag = TagModel.create_from_settings(tag_setting)
        
        assert tag is not None
        assert tag.get_name() == "test_tag"
        assert tag.display_name == "Test Tag Display"
        assert tag.description == "Test description"
    
    def test_create_from_settings_default_display_name(self):
        """测试从 settings 创建 TagModel（默认 display_name）"""
        from core.modules.tag.models.tag_model import TagModel
        
        tag_setting = {
            "name": "test_tag"
        }
        
        tag = TagModel.create_from_settings(tag_setting)
        
        assert tag is not None
        assert tag.display_name == "test_tag"  # 应该使用 name 作为默认值
    
    def test_is_setting_valid_valid(self):
        """测试 is_setting_valid（有效配置）"""
        from core.modules.tag.models.tag_model import TagModel
        
        tag_setting = {
            "name": "test_tag"
        }
        
        assert TagModel.is_setting_valid(tag_setting) is True
    
    def test_is_setting_valid_missing_name(self):
        """测试 is_setting_valid（缺少 name）"""
        from core.modules.tag.models.tag_model import TagModel
        
        tag_setting = {}
        
        assert TagModel.is_setting_valid(tag_setting) is False
    
    def test_is_setting_valid_empty_name(self):
        """测试 is_setting_valid（name 为空）"""
        from core.modules.tag.models.tag_model import TagModel
        
        tag_setting = {
            "name": ""
        }
        
        assert TagModel.is_setting_valid(tag_setting) is False
    
    def test_is_setting_valid_none_name(self):
        """测试 is_setting_valid（name 为 None）"""
        from core.modules.tag.models.tag_model import TagModel
        
        tag_setting = {
            "name": None
        }
        
        assert TagModel.is_setting_valid(tag_setting) is False
    
    def test_from_dict(self):
        """测试 from_dict（从字典创建 TagModel）"""
        from core.modules.tag.models.tag_model import TagModel
        
        tag_dict = {
            "id": 1,
            "tag_name": "test_tag",
            "scenario_id": 10,
            "display_name": "Test Tag Display",
            "description": "Test description",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-02"
        }
        
        tag = TagModel.from_dict(tag_dict)
        
        assert tag is not None
        assert tag.id == 1
        assert tag.tag_name == "test_tag"
        assert tag.scenario_id == 10
        assert tag.display_name == "Test Tag Display"
        assert tag.description == "Test description"
        assert tag.created_at == "2024-01-01"
        assert tag.updated_at == "2024-01-02"
    
    def test_to_dict(self):
        """测试 to_dict"""
        from core.modules.tag.models.tag_model import TagModel
        
        tag_setting = {
            "name": "test_tag",
            "display_name": "Test Tag Display",
            "description": "Test description"
        }
        
        tag = TagModel.create_from_settings(tag_setting)
        tag.id = 1
        tag.scenario_id = 10
        tag.created_at = "2024-01-01"
        tag.updated_at = "2024-01-02"
        
        result = tag.to_dict()
        
        assert result["id"] == 1
        assert result["tag_name"] == "test_tag"
        assert result["scenario_id"] == 10
        assert result["display_name"] == "Test Tag Display"
        assert result["description"] == "Test description"
        assert result["created_at"] == "2024-01-01"
        assert result["updated_at"] == "2024-01-02"
    
    def test_get_settings(self):
        """测试 get_settings"""
        from core.modules.tag.models.tag_model import TagModel
        
        tag_setting = {
            "name": "test_tag",
            "display_name": "Test Tag Display",
            "description": "Test description"
        }
        
        tag = TagModel.create_from_settings(tag_setting)
        settings = tag.get_settings()
        
        assert settings is not None
        assert settings["name"] == "test_tag"
        assert settings["display_name"] == "Test Tag Display"
        assert settings["description"] == "Test description"
    
    def test_has_meta_diff_different_display_name(self):
        """测试 _has_meta_diff（display_name 不同）"""
        from core.modules.tag.models.tag_model import TagModel
        
        tag_setting = {
            "name": "test_tag",
            "display_name": "New Display Name"
        }
        
        tag = TagModel.create_from_settings(tag_setting)
        
        db_meta = {
            "display_name": "Old Display Name",
            "description": ""
        }
        
        assert tag._has_meta_diff(db_meta) is True
    
    def test_has_meta_diff_different_description(self):
        """测试 _has_meta_diff（description 不同）"""
        from core.modules.tag.models.tag_model import TagModel
        
        tag_setting = {
            "name": "test_tag",
            "description": "New description"
        }
        
        tag = TagModel.create_from_settings(tag_setting)
        
        db_meta = {
            "display_name": "test_tag",
            "description": "Old description"
        }
        
        assert tag._has_meta_diff(db_meta) is True
    
    def test_has_meta_diff_no_diff(self):
        """测试 _has_meta_diff（无差异）"""
        from core.modules.tag.models.tag_model import TagModel
        
        tag_setting = {
            "name": "test_tag",
            "display_name": "Test Tag",
            "description": "Test description"
        }
        
        tag = TagModel.create_from_settings(tag_setting)
        
        db_meta = {
            "display_name": "Test Tag",
            "description": "Test description"
        }
        
        assert tag._has_meta_diff(db_meta) is False
