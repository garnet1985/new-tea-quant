"""
FileManager 单元测试
"""
import pytest
import tempfile
from pathlib import Path
from core.infra.project_context.file_manager import FileManager


class TestFileManager:
    """FileManager 测试类"""
    
    def test_find_file_existing(self):
        """测试查找存在的文件"""
        # 使用项目根目录的 README.md 作为测试文件
        root = PathManager.get_root()
        readme = root / "README.md"
        
        if readme.exists():
            found = FileManager.find_file("README.md", root, recursive=False)
            assert found is not None
            assert found.name == "README.md"
    
    def test_find_file_nonexistent(self):
        """测试查找不存在的文件"""
        root = PathManager.get_root()
        found = FileManager.find_file("nonexistent_file_12345.py", root)
        
        assert found is None
    
    def test_find_file_recursive(self):
        """测试递归查找文件"""
        root = PathManager.get_root()
        # 查找 __init__.py（应该能找到多个）
        found = FileManager.find_file("__init__.py", root, recursive=True)
        
        # 至少应该找到一个
        assert found is not None
    
    def test_read_file_existing(self):
        """测试读取存在的文件"""
        root = PathManager.get_root()
        readme = root / "README.md"
        
        if readme.exists():
            content = FileManager.read_file(readme)
            assert content is not None
            assert isinstance(content, str)
            assert len(content) > 0
    
    def test_read_file_nonexistent(self):
        """测试读取不存在的文件"""
        root = PathManager.get_root()
        nonexistent = root / "nonexistent_file_12345.txt"
        
        content = FileManager.read_file(nonexistent)
        assert content is None
    
    def test_file_exists(self):
        """测试检查文件是否存在"""
        root = PathManager.get_root()
        readme = root / "README.md"
        
        if readme.exists():
            assert FileManager.file_exists(readme) is True
        
        nonexistent = root / "nonexistent_file_12345.txt"
        assert FileManager.file_exists(nonexistent) is False
    
    def test_find_files(self):
        """测试查找所有匹配的文件"""
        root = PathManager.get_root()
        # 查找所有 __init__.py 文件
        init_files = FileManager.find_files("__init__.py", root, recursive=True)
        
        assert isinstance(init_files, list)
        # 应该找到一些 __init__.py 文件
        assert len(init_files) > 0
        # 验证所有文件都是 __init__.py
        for file_path in init_files:
            assert file_path.name == "__init__.py"


# 导入 PathManager 用于测试
from core.infra.project_context.path_manager import PathManager
