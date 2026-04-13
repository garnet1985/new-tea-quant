"""
TagHelper 单元测试
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


class TestTagHelper:
    """TagHelper 测试类"""
    
    def test_load_scenario_settings_success(self):
        """测试 load_scenario_settings（成功加载）"""
        from core.modules.tag.core.components.helper.tag_helper import TagHelper
        from pathlib import Path
        
        # Mock FileManager.find_file
        mock_settings_path = Path("/test/scenario/settings.py")
        
        with patch('core.modules.tag.core.components.helper.tag_helper.FileManager.find_file') as mock_find_file, \
             patch('core.modules.tag.core.components.helper.tag_helper.ConfigManager.load_python') as mock_load_python:
            
            mock_find_file.return_value = mock_settings_path
            mock_load_python.return_value = {
                "name": "test_scenario",
                "target_entity": {"type": "stock_kline_daily"},
                "is_enabled": True,
            "data": {"required": [{"data_id": "stock.kline", "params": {"term": "daily", "adjust": "qfq"}}]},
                "tags": [{"name": "tag1"}]
            }
            
            scenario_dir = Path("/test/scenario")
            settings_path, settings_dict = TagHelper.load_scenario_settings(scenario_dir)
            
            assert settings_path == mock_settings_path
            assert settings_dict is not None
            assert settings_dict["name"] == "test_scenario"
            mock_find_file.assert_called_once()
            mock_load_python.assert_called_once_with(mock_settings_path, var_name="Settings")
    
    def test_load_scenario_settings_file_not_found(self):
        """测试 load_scenario_settings（文件不存在）"""
        from core.modules.tag.core.components.helper.tag_helper import TagHelper
        from pathlib import Path
        
        with patch('core.modules.tag.core.components.helper.tag_helper.FileManager.find_file') as mock_find_file:
            mock_find_file.return_value = None
            
            scenario_dir = Path("/test/scenario")
            settings_path, settings_dict = TagHelper.load_scenario_settings(scenario_dir)
            
            assert settings_path is None
            assert settings_dict is None
    
    def test_load_scenario_settings_invalid_settings(self):
        """测试 load_scenario_settings（settings 无效）"""
        from core.modules.tag.core.components.helper.tag_helper import TagHelper
        from pathlib import Path
        
        mock_settings_path = Path("/test/scenario/settings.py")
        
        with patch('core.modules.tag.core.components.helper.tag_helper.FileManager.find_file') as mock_find_file, \
             patch('core.modules.tag.core.components.helper.tag_helper.ConfigManager.load_python') as mock_load_python:
            
            mock_find_file.return_value = mock_settings_path
            mock_load_python.return_value = None  # 返回 None
            
            scenario_dir = Path("/test/scenario")
            settings_path, settings_dict = TagHelper.load_scenario_settings(scenario_dir)
            
            assert settings_path is None
            assert settings_dict is None
    
    def test_load_scenario_settings_not_dict(self):
        """测试 load_scenario_settings（settings 不是字典）"""
        from core.modules.tag.core.components.helper.tag_helper import TagHelper
        from pathlib import Path
        
        mock_settings_path = Path("/test/scenario/settings.py")
        
        with patch('core.modules.tag.core.components.helper.tag_helper.FileManager.find_file') as mock_find_file, \
             patch('core.modules.tag.core.components.helper.tag_helper.ConfigManager.load_python') as mock_load_python:
            
            mock_find_file.return_value = mock_settings_path
            mock_load_python.return_value = "not a dict"  # 返回非字典类型
            
            scenario_dir = Path("/test/scenario")
            settings_path, settings_dict = TagHelper.load_scenario_settings(scenario_dir)
            
            assert settings_path is None
            assert settings_dict is None
    
    def test_load_worker_class_success(self):
        """测试 load_worker_class（成功加载）"""
        from core.modules.tag.core.components.helper.tag_helper import TagHelper
        from core.modules.tag.core.base_tag_worker import BaseTagWorker
        from pathlib import Path
        import types
        
        # 创建一个测试 worker 类
        class TestWorker(BaseTagWorker):
            def calculate_tag(self, data, as_of_date):
                return {"value": 1}
        
        mock_worker_path = Path("/test/scenario/tag_worker.py")
        
        with patch('core.modules.tag.core.components.helper.tag_helper.FileManager.find_file') as mock_find_file, \
             patch('importlib.util.spec_from_file_location') as mock_spec_from_file, \
             patch('importlib.util.module_from_spec') as mock_module_from_spec:
            
            mock_find_file.return_value = mock_worker_path
            
            # Mock spec
            mock_spec = MagicMock()
            mock_loader = MagicMock()
            mock_spec.loader = mock_loader
            mock_spec_from_file.return_value = mock_spec
            
            # Mock module - 使用 types.ModuleType 创建真实模块对象
            mock_module = types.ModuleType('tag_worker')
            mock_module.TestWorker = TestWorker
            mock_module.BaseTagWorker = BaseTagWorker
            mock_module_from_spec.return_value = mock_module
            
            scenario_folder = Path("/test/scenario")
            worker_path, worker_class = TagHelper.load_worker_class(scenario_folder)
            
            assert worker_path == mock_worker_path
            assert worker_class == TestWorker
    
    def test_load_worker_class_file_not_found(self):
        """测试 load_worker_class（文件不存在）"""
        from core.modules.tag.core.components.helper.tag_helper import TagHelper
        from pathlib import Path
        
        with patch('core.modules.tag.core.components.helper.tag_helper.FileManager.find_file') as mock_find_file:
            mock_find_file.return_value = None
            
            scenario_folder = Path("/test/scenario")
            worker_path, worker_class = TagHelper.load_worker_class(scenario_folder)
            
            assert worker_path is None
            assert worker_class is None
    
    def test_load_worker_class_no_worker_class(self):
        """测试 load_worker_class（没有 worker 类）"""
        from core.modules.tag.core.components.helper.tag_helper import TagHelper
        from pathlib import Path
        import types
        
        mock_worker_path = Path("/test/scenario/tag_worker.py")
        
        with patch('core.modules.tag.core.components.helper.tag_helper.FileManager.find_file') as mock_find_file, \
             patch('importlib.util.spec_from_file_location') as mock_spec_from_file, \
             patch('importlib.util.module_from_spec') as mock_module_from_spec:
            
            mock_find_file.return_value = mock_worker_path
            
            # Mock spec
            mock_spec = MagicMock()
            mock_loader = MagicMock()
            mock_spec.loader = mock_loader
            mock_spec_from_file.return_value = mock_spec
            
            # Mock module（没有 worker 类）- 使用 types.ModuleType 创建真实模块对象
            mock_module = types.ModuleType('tag_worker')
            mock_module.SomeOtherClass = object
            mock_module_from_spec.return_value = mock_module
            
            scenario_folder = Path("/test/scenario")
            worker_path, worker_class = TagHelper.load_worker_class(scenario_folder)
            
            assert worker_path is None
            assert worker_class is None
    
    def test_load_worker_class_spec_none(self):
        """测试 load_worker_class（spec 为 None）"""
        from core.modules.tag.core.components.helper.tag_helper import TagHelper
        from pathlib import Path
        
        mock_worker_path = Path("/test/scenario/tag_worker.py")
        
        with patch('core.modules.tag.core.components.helper.tag_helper.FileManager.find_file') as mock_find_file, \
             patch('importlib.util.spec_from_file_location') as mock_spec_from_file:
            
            mock_find_file.return_value = mock_worker_path
            mock_spec_from_file.return_value = None  # spec 为 None
            
            scenario_folder = Path("/test/scenario")
            worker_path, worker_class = TagHelper.load_worker_class(scenario_folder)
            
            assert worker_path is None
            assert worker_class is None
    
    def test_load_worker_class_loader_none(self):
        """测试 load_worker_class（loader 为 None）"""
        from core.modules.tag.core.components.helper.tag_helper import TagHelper
        from pathlib import Path
        
        mock_worker_path = Path("/test/scenario/tag_worker.py")
        
        with patch('core.modules.tag.core.components.helper.tag_helper.FileManager.find_file') as mock_find_file, \
             patch('importlib.util.spec_from_file_location') as mock_spec_from_file:
            
            mock_find_file.return_value = mock_worker_path
            
            # Mock spec with None loader
            mock_spec = MagicMock()
            mock_spec.loader = None
            mock_spec_from_file.return_value = mock_spec
            
            scenario_folder = Path("/test/scenario")
            worker_path, worker_class = TagHelper.load_worker_class(scenario_folder)
            
            assert worker_path is None
            assert worker_class is None
