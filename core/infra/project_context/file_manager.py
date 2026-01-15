"""
File Manager - 文件管理器

职责：文件查找、读取、存在性检查等操作。

设计原则：
- 使用 pathlib.Path 而不是字符串路径
- 提供静态方法，无状态
- 文件不存在时返回 None 或空列表
"""

from pathlib import Path
from typing import Optional, List
import os


class FileManager:
    """文件管理器 - 文件查找、读取等操作"""
    
    @staticmethod
    def find_file(
        filename: str,
        base_dir: Path,
        recursive: bool = True
    ) -> Optional[Path]:
        """
        查找文件
        
        Args:
            filename: 文件名（如 "settings.py"）
            base_dir: 基础目录
            recursive: 是否递归查找
        
        Returns:
            找到的文件路径，如果未找到返回 None
        """
        # 转换为绝对路径
        if not base_dir.is_absolute():
            base_dir = base_dir.resolve()
        
        if not base_dir.exists() or not base_dir.is_dir():
            return None
        
        # 非递归查找（只在当前目录）
        if not recursive:
            file_path = base_dir / filename
            if file_path.exists() and file_path.is_file():
                return file_path.resolve()
            return None
        
        # 递归查找
        for root, dirs, files in os.walk(base_dir):
            if filename in files:
                found_path = Path(root) / filename
                return found_path.resolve()
        
        return None
    
    @staticmethod
    def find_files(
        filename: str,
        base_dir: Path,
        recursive: bool = True
    ) -> List[Path]:
        """
        查找所有匹配的文件
        
        Args:
            filename: 文件名
            base_dir: 基础目录
            recursive: 是否递归查找
        
        Returns:
            找到的文件路径列表
        """
        # 转换为绝对路径
        if not base_dir.is_absolute():
            base_dir = base_dir.resolve()
        
        if not base_dir.exists() or not base_dir.is_dir():
            return []
        
        found_files = []
        
        # 非递归查找（只在当前目录）
        if not recursive:
            file_path = base_dir / filename
            if file_path.exists() and file_path.is_file():
                found_files.append(file_path.resolve())
            return found_files
        
        # 递归查找
        for root, dirs, files in os.walk(base_dir):
            if filename in files:
                found_path = Path(root) / filename
                found_files.append(found_path.resolve())
        
        return found_files
    
    @staticmethod
    def read_file(path: Path, encoding: str = "utf-8") -> Optional[str]:
        """
        读取文件内容
        
        Args:
            path: 文件路径
            encoding: 文件编码
        
        Returns:
            文件内容，如果文件不存在或读取失败返回 None
        """
        try:
            # 转换为绝对路径
            if not path.is_absolute():
                path = path.resolve()
            
            if not path.exists() or not path.is_file():
                return None
            
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except Exception:
            return None
    
    @staticmethod
    def file_exists(path: Path) -> bool:
        """
        检查文件是否存在
        
        Args:
            path: 文件路径
        
        Returns:
            文件是否存在且是文件（不是目录）
        """
        try:
            # 转换为绝对路径
            if not path.is_absolute():
                path = path.resolve()
            
            return path.exists() and path.is_file()
        except Exception:
            return False
    
    @staticmethod
    def dir_exists(path: Path) -> bool:
        """
        检查目录是否存在
        
        Args:
            path: 目录路径
        
        Returns:
            目录是否存在且是目录（不是文件）
        """
        try:
            # 转换为绝对路径
            if not path.is_absolute():
                path = path.resolve()
            
            return path.exists() and path.is_dir()
        except Exception:
            return False
    
    @staticmethod
    def ensure_dir(path: Path) -> Path:
        """
        确保目录存在（不存在则创建）
        
        Args:
            path: 目录路径
        
        Returns:
            目录路径（用于链式调用）
        """
        # 转换为绝对路径
        if not path.is_absolute():
            path = path.resolve()
        
        path.mkdir(parents=True, exist_ok=True)
        return path
