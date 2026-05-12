"""
PathManager 单元测试
"""
import pytest
from pathlib import Path

from core.infra.project_context.path_manager import PathManager


def _fake_repo_with_userspace(tmp_path: Path, *, with_strategies: bool = True, with_config: bool = False) -> Path:
    """在临时目录构造最小「含 userspace」仓库树（CI 检出未必自带 userspace/）。"""
    fake_root = tmp_path / "repo"
    fake_root.mkdir()
    (fake_root / "README.md").touch()
    us = fake_root / "userspace"
    us.mkdir()
    if with_strategies:
        (us / "strategies").mkdir()
    if with_config:
        (us / "config").mkdir()
    return fake_root


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
    
    def test_userspace(self, tmp_path, monkeypatch):
        """测试获取 userspace 目录（默认 <root>/userspace；仓库可不自带，由安装创建）"""
        fake_root = _fake_repo_with_userspace(tmp_path, with_strategies=True)
        monkeypatch.setattr(PathManager, "_root_cache", fake_root)
        PathManager.invalidate_userspace_cache()
        try:
            userspace_dir = PathManager.userspace()

            assert isinstance(userspace_dir, Path)
            assert userspace_dir == fake_root / "userspace"
            assert userspace_dir.exists()
            assert (userspace_dir / "strategies").exists()
        finally:
            PathManager.invalidate_userspace_cache()

    def test_config(self, tmp_path, monkeypatch):
        """测试获取 config 目录（userspace/config）"""
        fake_root = _fake_repo_with_userspace(tmp_path, with_strategies=False, with_config=True)
        monkeypatch.setattr(PathManager, "_root_cache", fake_root)
        PathManager.invalidate_userspace_cache()
        try:
            config_dir = PathManager.config()

            assert isinstance(config_dir, Path)
            assert config_dir == fake_root / "userspace" / "config"
            assert config_dir.exists()
        finally:
            PathManager.invalidate_userspace_cache()
    
    def test_strategy(self):
        """测试获取策略目录"""
        strategy_dir = PathManager.strategy("example")
        
        assert isinstance(strategy_dir, Path)
        # 策略目录路径应该正确
        assert "example" in str(strategy_dir)

    def test_backup_paths(self):
        """备份目录落在 userspace/backup 约定下"""
        root = PathManager.get_root()
        backup_dir = PathManager.backup()
        backup_data_dir = PathManager.backup_data()

        assert isinstance(backup_dir, Path)
        assert isinstance(backup_data_dir, Path)
        assert backup_data_dir == backup_dir / "data"
        assert backup_dir.is_relative_to(root)
        assert "userspace" in backup_dir.parts and "backup" in backup_dir.parts
    
    def test_root_caching(self):
        """测试根目录缓存"""
        root1 = PathManager.get_root()
        root2 = PathManager.get_root()
        
        # 应该返回同一个对象（缓存）
        assert root1 is root2
