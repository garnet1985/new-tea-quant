"""
文件工具类

提供文件查找、读取等静态方法
"""
from typing import Optional, List
from pathlib import Path
import os


class FileUtil:
    """文件工具类（全部静态方法）"""
    
    @staticmethod
    def find_file_in_folder(
        file_name: str,
        folder_path: str,
        is_recursively: bool = True
    ) -> Optional[str]:
        """
        在文件夹中查找文件
        
        Args:
            file_name: 文件名（如 "settings.py", "calculator.py"）
            folder_path: 文件夹路径（相对路径或绝对路径）
            is_recursively: 是否递归查找（默认 True）
            
        Returns:
            str: 找到的文件绝对路径，如果未找到返回 None
            
        Examples:
            >>> # 在当前目录查找
            >>> file_path = FileUtil.find_file_in_folder("settings.py", ".")
            >>> 
            >>> # 递归查找
            >>> file_path = FileUtil.find_file_in_folder("config.json", "/path/to/folder", is_recursively=True)
            >>> 
            >>> # 非递归查找（只在当前目录）
            >>> file_path = FileUtil.find_file_in_folder("README.md", "/path/to/folder", is_recursively=False)
        """
        folder = Path(folder_path)
        
        # 转换为绝对路径
        if not folder.is_absolute():
            folder = folder.resolve()
        
        if not folder.exists():
            return None
        
        if not folder.is_dir():
            return None
        
        # 非递归查找（只在当前目录）
        if not is_recursively:
            file_path = folder / file_name
            if file_path.exists() and file_path.is_file():
                return str(file_path.resolve())
            return None
        
        # 递归查找
        for root, dirs, files in os.walk(folder):
            if file_name in files:
                found_path = Path(root) / file_name
                return str(found_path.resolve())
        
        return None
    
    @staticmethod
    def find_files_in_folder(
        file_name: str,
        folder_path: str,
        is_recursively: bool = True
    ) -> List[str]:
        """
        在文件夹中查找所有匹配的文件（可能有多个）
        
        Args:
            file_name: 文件名（如 "settings.py", "calculator.py"）
            folder_path: 文件夹路径（相对路径或绝对路径）
            is_recursively: 是否递归查找（默认 True）
            
        Returns:
            List[str]: 找到的文件绝对路径列表（可能为空）
            
        Examples:
            >>> # 查找所有 settings.py 文件
            >>> file_paths = FileUtil.find_files_in_folder("settings.py", "/path/to/tags")
        """
        folder = Path(folder_path)
        
        # 转换为绝对路径
        if not folder.is_absolute():
            folder = folder.resolve()
        
        if not folder.exists() or not folder.is_dir():
            return []
        
        found_files = []
        
        # 非递归查找（只在当前目录）
        if not is_recursively:
            file_path = folder / file_name
            if file_path.exists() and file_path.is_file():
                found_files.append(str(file_path.resolve()))
            return found_files
        
        # 递归查找
        for root, dirs, files in os.walk(folder):
            if file_name in files:
                found_path = Path(root) / file_name
                found_files.append(str(found_path.resolve()))
        
        return found_files
    
    @staticmethod
    def read_file_content(file_path: str, encoding: str = "utf-8") -> Optional[str]:
        """
        读取文件内容
        
        Args:
            file_path: 文件路径（相对路径或绝对路径）
            encoding: 文件编码（默认 utf-8）
            
        Returns:
            str: 文件内容，如果文件不存在或读取失败返回 None
        """
        try:
            file = Path(file_path)
            if not file.is_absolute():
                file = file.resolve()
            
            if not file.exists() or not file.is_file():
                return None
            
            with open(file, "r", encoding=encoding) as f:
                return f.read()
        except Exception:
            return None
    
    @staticmethod
    def file_exists(file_path: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            file_path: 文件路径（相对路径或绝对路径）
            
        Returns:
            bool: 文件是否存在且是文件（不是目录）
        """
        try:
            file = Path(file_path)
            if not file.is_absolute():
                file = file.resolve()
            
            return file.exists() and file.is_file()
        except Exception:
            return False
    
    @staticmethod
    def dir_exists(dir_path: str) -> bool:
        """
        检查目录是否存在
        
        Args:
            dir_path: 目录路径（相对路径或绝对路径）
            
        Returns:
            bool: 目录是否存在且是目录（不是文件）
        """
        try:
            dir_path_obj = Path(dir_path)
            if not dir_path_obj.is_absolute():
                dir_path_obj = dir_path_obj.resolve()
            
            return dir_path_obj.exists() and dir_path_obj.is_dir()
        except Exception:
            return False
