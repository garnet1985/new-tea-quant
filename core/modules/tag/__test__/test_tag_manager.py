"""
TagManager 单元测试
"""
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False


class TestTagManager:
    """TagManager 测试类"""
    
    @patch('core.modules.tag.tag_manager.DataManager')
    @patch('core.modules.tag.tag_manager.get_scenarios_root')
    def test_init(self, mock_get_scenarios_root, mock_data_manager):
        """测试 TagManager 初始化"""
        from core.modules.tag.tag_manager import TagManager
        from pathlib import Path
        
        # Mock scenarios root
        mock_root = Path("/test/scenarios")
        mock_get_scenarios_root.return_value = mock_root
        
        # Mock DataManager
        mock_data_mgr = MagicMock()
        mock_tag_service = MagicMock()
        mock_data_mgr.stock.tags = mock_tag_service
        mock_data_manager.return_value = mock_data_mgr
        
        # Mock scenario discovery
        with patch.object(TagManager, '_discover_scenarios_from_folder') as mock_discover:
            manager = TagManager(is_verbose=False)
            
            assert manager.is_verbose is False
            assert manager.data_mgr == mock_data_mgr
            assert manager.tag_data_service == mock_tag_service
            assert manager.scenario_cache == {}
            assert manager.entity_list_cache == {}
            mock_discover.assert_called_once()
    
    @patch('core.modules.tag.tag_manager.DataManager')
    @patch('core.modules.tag.tag_manager.get_scenarios_root')
    def test_refresh_scenario(self, mock_get_scenarios_root, mock_data_manager):
        """测试 refresh_scenario"""
        from core.modules.tag.tag_manager import TagManager
        
        mock_get_scenarios_root.return_value = Path("/test/scenarios")
        mock_data_mgr = MagicMock()
        mock_data_mgr.stock.tags = MagicMock()
        mock_data_manager.return_value = mock_data_mgr
        
        with patch.object(TagManager, '_discover_scenarios_from_folder') as mock_discover, \
             patch.object(TagManager, '_clear_cache') as mock_clear_cache:
            
            manager = TagManager(is_verbose=False)
            # 重置 mock 调用计数（因为 __init__ 中已经调用了一次）
            mock_discover.reset_mock()
            manager.scenario_cache = {"test": "cache"}
            manager.entity_list_cache = {"test": "cache"}
            
            manager.refresh_scenario()
            
            mock_clear_cache.assert_called_once()
            mock_discover.assert_called_once()
    
    @patch('core.modules.tag.tag_manager.DataManager')
    @patch('core.modules.tag.tag_manager.get_scenarios_root')
    def test_execute_with_scenario_name(self, mock_get_scenarios_root, mock_data_manager):
        """测试 execute（指定 scenario_name）"""
        from core.modules.tag.tag_manager import TagManager
        
        mock_get_scenarios_root.return_value = Path("/test/scenarios")
        mock_data_mgr = MagicMock()
        mock_data_mgr.stock.tags = MagicMock()
        mock_data_manager.return_value = mock_data_mgr
        
        with patch.object(TagManager, '_discover_scenarios_from_folder'), \
             patch.object(TagManager, '_execute_single') as mock_execute_single:
            
            manager = TagManager(is_verbose=False)
            manager.execute(scenario_name="test_scenario")
            
            mock_execute_single.assert_called_once_with("test_scenario")
    
    @patch('core.modules.tag.tag_manager.DataManager')
    @patch('core.modules.tag.tag_manager.get_scenarios_root')
    def test_execute_with_settings(self, mock_get_scenarios_root, mock_data_manager):
        """测试 execute（指定 settings）"""
        from core.modules.tag.tag_manager import TagManager
        
        mock_get_scenarios_root.return_value = Path("/test/scenarios")
        mock_data_mgr = MagicMock()
        mock_data_mgr.stock.tags = MagicMock()
        mock_data_manager.return_value = mock_data_mgr
        
        settings = {
            "name": "test_scenario",
            "target_entity": {"type": "stock_kline_daily"},
            "is_enabled": True,
            "data": {"required": [{"data_id": "stock.kline", "params": {"term": "daily", "adjust": "qfq"}}]},
            "tags": [{"name": "tag1"}],
            "incremental_required_records_before_as_of_date": 10
        }
        
        with patch.object(TagManager, '_discover_scenarios_from_folder'), \
             patch.object(TagManager, '_execute_single_from_tmp_settings') as mock_execute_tmp:
            
            manager = TagManager(is_verbose=False)
            manager.execute(settings=settings)
            
            mock_execute_tmp.assert_called_once_with(settings)
    
    @patch('core.modules.tag.tag_manager.DataManager')
    @patch('core.modules.tag.tag_manager.get_scenarios_root')
    def test_execute_all(self, mock_get_scenarios_root, mock_data_manager):
        """测试 execute（执行所有 scenarios）"""
        from core.modules.tag.tag_manager import TagManager
        
        mock_get_scenarios_root.return_value = Path("/test/scenarios")
        mock_data_mgr = MagicMock()
        mock_data_mgr.stock.tags = MagicMock()
        mock_data_manager.return_value = mock_data_mgr
        
        with patch.object(TagManager, '_discover_scenarios_from_folder'), \
             patch.object(TagManager, '_execute_single') as mock_execute_single:
            
            manager = TagManager(is_verbose=False)
            manager.scenario_cache = {
                "scenario1": {},
                "scenario2": {}
            }
            
            manager.execute()
            
            assert mock_execute_single.call_count == 2
            mock_execute_single.assert_any_call("scenario1")
            mock_execute_single.assert_any_call("scenario2")
    
    @patch('core.modules.tag.tag_manager.DataManager')
    @patch('core.modules.tag.tag_manager.get_scenarios_root')
    def test_discover_scenarios_from_folder_not_exists(self, mock_get_scenarios_root, mock_data_manager):
        """测试 _discover_scenarios_from_folder（目录不存在）"""
        from core.modules.tag.tag_manager import TagManager
        
        mock_root = Path("/test/scenarios")
        mock_get_scenarios_root.return_value = mock_root
        
        mock_data_mgr = MagicMock()
        mock_data_mgr.stock.tags = MagicMock()
        mock_data_manager.return_value = mock_data_mgr
        
        with patch.object(Path, 'exists', return_value=False):
            manager = TagManager(is_verbose=False)
            
            assert manager.scenario_cache == {}
    
    @patch('core.modules.tag.tag_manager.DataManager')
    @patch('core.modules.tag.tag_manager.get_scenarios_root')
    def test_load_scenario_from_cache_by_name_exists(self, mock_get_scenarios_root, mock_data_manager):
        """测试 _load_scenario_from_cache_by_name（存在）"""
        from core.modules.tag.tag_manager import TagManager
        
        mock_get_scenarios_root.return_value = Path("/test/scenarios")
        mock_data_mgr = MagicMock()
        mock_data_mgr.stock.tags = MagicMock()
        mock_data_manager.return_value = mock_data_mgr
        
        with patch.object(TagManager, '_discover_scenarios_from_folder'):
            manager = TagManager(is_verbose=False)
            manager.scenario_cache = {
                "test_scenario": {
                    "settings": {"name": "test_scenario"},
                    "worker_class": None
                }
            }
            
            result = manager._load_scenario_from_cache_by_name("test_scenario")
            
            assert result is not None
            assert result["settings"]["name"] == "test_scenario"
    
    @patch('core.modules.tag.tag_manager.DataManager')
    @patch('core.modules.tag.tag_manager.get_scenarios_root')
    def test_load_scenario_from_cache_by_name_not_exists(self, mock_get_scenarios_root, mock_data_manager):
        """测试 _load_scenario_from_cache_by_name（不存在）"""
        from core.modules.tag.tag_manager import TagManager
        
        mock_get_scenarios_root.return_value = Path("/test/scenarios")
        mock_data_mgr = MagicMock()
        mock_data_mgr.stock.tags = MagicMock()
        mock_data_manager.return_value = mock_data_mgr
        
        with patch.object(TagManager, '_discover_scenarios_from_folder'):
            manager = TagManager(is_verbose=False)
            manager.scenario_cache = {}
            
            result = manager._load_scenario_from_cache_by_name("test_scenario")
            
            assert result is None

    @patch('core.modules.tag.tag_manager.DataManager')
    @patch('core.modules.tag.tag_manager.get_scenarios_root')
    def test_run_execute_pipeline_general_uses_general_owner(self, mock_get_scenarios_root, mock_data_manager):
        """测试 general 模式固定使用 __general__ owner"""
        from core.modules.tag.tag_manager import TagManager

        mock_get_scenarios_root.return_value = Path("/test/scenarios")
        mock_data_mgr = MagicMock()
        mock_tag_service = MagicMock()
        mock_data_mgr.stock.tags = mock_tag_service
        mock_data_manager.return_value = mock_data_mgr

        with patch.object(TagManager, '_discover_scenarios_from_folder'), \
             patch.object(TagManager, '_get_worker_class', return_value=MagicMock()), \
             patch.object(TagManager, '_build_jobs', return_value=[] ) as mock_build_jobs:
            manager = TagManager(is_verbose=False)
            scenario_model = MagicMock()
            scenario_model.is_enabled.return_value = True
            scenario_model.get_name.return_value = "macro_general"
            scenario_model.get_settings.return_value = {
                "name": "macro_general",
                "tag_target_type": "general",
                "data": {
                    "required": [{"data_id": "macro.gdp", "params": {}}],
                    "tag_time_axis_based_on": "macro.gdp",
                },
                "tags": [{"name": "macro_tag"}],
            }
            manager._run_execute_pipeline(scenario_model)

            args, _ = mock_build_jobs.call_args
            assert args[0] == ["__general__"]
