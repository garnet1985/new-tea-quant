"""
文件工具模块

提供文件查找、读取等工具方法
"""
from app.core.utils.file.file_util import FileUtil

# 为了向后兼容，导出静态方法作为函数
find_file_in_folder = FileUtil.find_file_in_folder

__all__ = ['FileUtil', 'find_file_in_folder']
