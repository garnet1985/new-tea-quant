"""
宏观经济数据服务模块（MacroDataService）

目录结构：
- macro_data_service.py  - 主服务类
- macro_queries.py       - 复杂 SQL 查询（可选，未来按需拆分）
- macro_helpers.py       - 辅助方法（可选，未来按需拆分）
"""

from .macro_data_service import MacroDataService

__all__ = [
    'MacroDataService',
]

