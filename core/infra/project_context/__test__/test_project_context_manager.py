"""
ProjectContext 单元测试

测试对外唯一入口的API
"""
import pytest
from pathlib import Path
from core.infra.project_context import ProjectContext


class TestProjectContext:
    """ProjectContext 测试类"""

    # ========== 路径核心 API 测试（5个）==========

    def test_get_project_root(self):
        """测试获取项目根目录"""
        root = ProjectContext.path.get_project_root()
        assert root is not None
        assert isinstance(root, Path)
        # 应该包含 .git 或其他根目录标记
        assert (root / ".git").exists() or (root / "pyproject.toml").exists()

    def test_get_core_root(self):
        """测试获取 core 目录"""
        core_dir = ProjectContext.path.get_core_root()
        assert core_dir is not None
        assert isinstance(core_dir, Path)
        # 应该是 project_root/core
        assert core_dir.name == "core"

    def test_get_userspace_root(self):
        """测试获取 userspace 目录"""
        userspace_dir = ProjectContext.path.get_userspace_root()
        assert userspace_dir is not None
        assert isinstance(userspace_dir, Path)
        # 应该是 userspace 目录
        assert userspace_dir.name == "userspace"

    def test_get_strategy_directory(self):
        """测试获取策略目录"""
        # 假设有一个策略（如果不存在，测试会失败）
        strategy_dir = ProjectContext.path.get_strategy_directory("example")
        assert strategy_dir is not None
        assert isinstance(strategy_dir, Path)
        assert strategy_dir.name == "example"

    def test_get_tag_directory(self):
        """测试获取 Tag 目录"""
        tag_dir = ProjectContext.path.get_tag_directory("example")
        assert tag_dir is not None
        assert isinstance(tag_dir, Path)
        assert tag_dir.name == "example"

    # ========== 元数据核心 API 测试（2个）==========

    def test_core_version(self):
        """测试获取 core 版本号"""
        version = ProjectContext.meta.core_version()

        # 如果 core_meta.json 存在，应该返回版本号字符串
        if version is not None:
            assert isinstance(version, str)
            # 版本号格式：x.y.z
            assert len(version.split(".")) == 3

    def test_core_info(self):
        """测试获取 core meta 信息"""
        core_info = ProjectContext.meta.core_info()

        # 如果 core_meta.json 存在，应该返回字典
        if core_info is not None:
            assert isinstance(core_info, dict)
            assert "version" in core_info

    # ========== 缓存管理 API 测试（1个）==========

    def test_clear_userspace_cache(self):
        """测试清理 userspace 路径缓存"""
        # 先获取 userspace（会缓存）
        userspace1 = ProjectContext.path.get_userspace_root()
        # 清理缓存
        ProjectContext.cache.clear_userspace_cache()
        # 再次获取（会重新计算）
        userspace2 = ProjectContext.path.get_userspace_root()
        # 应该返回相同的路径
        assert userspace1 == userspace2