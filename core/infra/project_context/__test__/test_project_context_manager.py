"""
ProjectContextManager 单元测试
"""
import pytest
from core.infra.project_context.project_context_manager import ProjectContextManager
from core.infra.project_context import PathManager, FileManager, ConfigManager


class TestProjectContextManager:
    """ProjectContextManager 测试类"""
    
    def test_init(self):
        """测试初始化"""
        ctx = ProjectContextManager()
        
        # 验证 Manager 属性
        assert ctx.path == PathManager
        assert ctx.file == FileManager
        assert ctx.config == ConfigManager
    
    def test_core_info(self):
        """测试获取 core meta 信息"""
        ctx = ProjectContextManager()
        core_info = ctx.core_info()
        
        # 如果 core_meta.json 存在，应该返回字典
        if core_info is not None:
            assert isinstance(core_info, dict)
            assert "version" in core_info
            assert "release_date" in core_info
    
    def test_core_version(self):
        """测试获取 core 版本号"""
        ctx = ProjectContextManager()
        version = ctx.core_version()
        
        # 如果 core_meta.json 存在，应该返回版本号字符串
        if version is not None:
            assert isinstance(version, str)
            # 版本号格式：x.y.z
            assert len(version.split(".")) == 3
    
    def test_path_access(self):
        """测试路径访问"""
        ctx = ProjectContextManager()
        
        # 测试通过 Facade 访问 PathManager
        root = ctx.path.get_root()
        assert root is not None
        
        core_dir = ctx.path.core()
        assert core_dir is not None
    
    def test_file_access(self):
        """测试文件访问"""
        ctx = ProjectContextManager()
        
        # 测试通过 Facade 访问 FileManager
        root = ctx.path.get_root()
        readme = ctx.file.find_file("README.md", root, recursive=False)
        
        # 如果 README.md 存在，应该能找到
        if (root / "README.md").exists():
            assert readme is not None
    
    def test_config_access(self):
        """测试配置访问"""
        ctx = ProjectContextManager()
        
        # 测试通过 Facade 访问 ConfigManager
        start_date = ctx.config.get_default_start_date()
        assert isinstance(start_date, str)
        
        db_type = ctx.config.get_database_type()
        assert isinstance(db_type, str)
