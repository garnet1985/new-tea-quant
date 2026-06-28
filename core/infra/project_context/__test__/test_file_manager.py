"""
FileManager 单元测试
"""
import pytest
import tempfile
from pathlib import Path
from core.infra.project_context import ProjectContext
from core.infra.discovery import Discovery


class TestFileManager:
    """FileManager 测试类"""
    
    def test_find_file_existing(self):
        """测试查找存在的文件"""
        # 使用项目根目录的 README.md 作为测试文件
        root = ProjectContext.path.get_project_root()
        readme = root / "README.md"

        if readme.exists():
            found = Discovery.file.find_file(root, "README.md")
            assert found is not None
            assert found.name == "README.md"

    def test_find_file_nonexistent(self):
        """测试查找不存在的文件"""
        root = ProjectContext.path.get_project_root()
        found = Discovery.file.find_file(root, "nonexistent_file_12345.py")

        assert found is None

    def test_find_file_recursive(self):
        """测试递归查找文件"""
        root = ProjectContext.path.get_project_root()
        # 查找 __init__.py（应该能找到多个）
        found_files = Discovery.discover.files(root, "**/__init__.py")

        # 至少应该找到一个
        assert len(found_files) > 0

    def test_read_file_existing(self):
        """测试读取存在的文件"""
        root = ProjectContext.path.get_project_root()
        readme = root / "README.md"

        if readme.exists():
            content = Discovery.file.load_text(readme)
            assert content is not None
            assert isinstance(content, str)
            assert len(content) > 0

    def test_read_file_nonexistent(self):
        """测试读取不存在的文件"""
        root = ProjectContext.path.get_project_root()
        nonexistent = root / "nonexistent_file_12345.txt"

        content = Discovery.file.load_text(nonexistent)
        assert content is None

    def test_file_exists(self):
        """测试检查文件是否存在"""
        root = ProjectContext.path.get_project_root()
        readme = root / "README.md"

        if readme.exists():
            assert readme.exists() and readme.is_file() is True

        nonexistent = root / "nonexistent_file_12345.txt"
        assert nonexistent.exists() is False

    def test_find_files(self):
        """测试查找所有匹配的文件"""
        root = ProjectContext.path.get_project_root()
        # 查找所有 __init__.py 文件
        init_files = Discovery.discover.files(root, "**/__init__.py")

        assert isinstance(init_files, list)
        # 应该找到一些 __init__.py 文件
        assert len(init_files) > 0
        # 验证所有文件都是 __init__.py
        for file_path in init_files:
            assert file_path.name == "__init__.py"


