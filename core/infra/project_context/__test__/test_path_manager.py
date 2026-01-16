"""
PathManager 单元测试
"""
import pytest
from pathlib import Path
from core.infra.project_context.path_manager import PathManager


class TestPathManager:
    """PathManager 测试类"""
    
    def test_get_root(self):
        """测试获取项目根目录"""
        root = PathManager.get_root()
        
        # 验证返回的是 Path 对象
        assert isinstance(root, Path)
        
        # 验证根目录存在
        assert root.exists()
        assert root.is_dir()
        
        # 验证根目录包含项目标记文件
        assert (root / "README.md").exists() or (root / ".git").exists()
    
    def test_core(self):
        """测试获取 core 目录"""
        core_dir = PathManager.core()
        
        assert isinstance(core_dir, Path)
        assert core_dir.exists()
        assert (core_dir / "infra").exists()
    
    def test_userspace(self):
        """测试获取 userspace 目录"""
        userspace_dir = PathManager.userspace()
        
        assert isinstance(userspace_dir, Path)
        assert userspace_dir.exists()
        assert (userspace_dir / "strategies").exists()
    
    def test_config(self):
        """测试获取 config 目录"""
        config_dir = PathManager.config()
        
        assert isinstance(config_dir, Path)
        # config 目录应该存在
        assert config_dir.exists()
    
    def test_strategy(self):
        """测试获取策略目录"""
        strategy_dir = PathManager.strategy("example")
        
        assert isinstance(strategy_dir, Path)
        # 策略目录路径应该正确
        assert "example" in str(strategy_dir)
    
    def test_root_caching(self):
        """测试根目录缓存"""
        root1 = PathManager.get_root()
        root2 = PathManager.get_root()
        
        # 应该返回同一个对象（缓存）
        assert root1 is root2
