"""
BaseDatabaseAdapter - 数据库适配器基类

定义统一的数据库操作接口，支持多种数据库后端。
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, ContextManager
from contextlib import contextmanager
from loguru import logger


class BaseDatabaseAdapter(ABC):
    """
    数据库适配器抽象基类
    
    所有数据库适配器必须实现此接口，提供统一的数据库操作。
    """
    
    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> Any:
        """
        建立数据库连接
        
        Args:
            config: 数据库配置字典
            
        Returns:
            数据库连接对象（类型取决于具体实现）
        """
        pass
    
    @abstractmethod
    def close(self):
        """关闭数据库连接"""
        pass
    
    @abstractmethod
    def execute_query(self, query: str, params: Any = None) -> List[Dict[str, Any]]:
        """
        执行查询语句，返回字典列表
        
        Args:
            query: SQL 查询语句（使用占位符，由 get_placeholder() 决定）
            params: 查询参数（元组、列表或字典）
            
        Returns:
            查询结果列表，每个元素是字典（字段名 -> 值）
        """
        pass
    
    @abstractmethod
    def execute_write(self, query: str, params: Any = None) -> int:
        """
        执行写入语句（INSERT、UPDATE、DELETE）
        
        Args:
            query: SQL 写入语句
            params: 查询参数
            
        Returns:
            影响的行数
        """
        pass
    
    @abstractmethod
    def execute_batch(self, query: str, params_list: List[Any]) -> int:
        """
        批量执行写入语句
        
        Args:
            query: SQL 写入语句
            params_list: 参数列表（每个元素对应一条记录）
            
        Returns:
            总影响的行数
        """
        pass
    
    @abstractmethod
    @contextmanager
    def transaction(self) -> ContextManager[Any]:
        """
        事务上下文管理器
        
        使用方式:
            with adapter.transaction() as cursor:
                cursor.execute("INSERT ...")
                cursor.execute("UPDATE ...")
                # 自动提交或回滚
        """
        pass
    
    @abstractmethod
    def get_placeholder(self) -> str:
        """
        返回占位符类型
        
        Returns:
            '%s' (PostgreSQL/MySQL) 或 '?' (SQLite)
        """
        pass
    
    @abstractmethod
    def get_connection(self) -> Any:
        """
        获取数据库连接对象（用于需要直接访问连接的场景）
        
        Returns:
            数据库连接对象
        """
        pass
    
    @abstractmethod
    def is_table_exists(self, table_name: str) -> bool:
        """
        检查表是否存在
        
        Args:
            table_name: 表名
            
        Returns:
            是否存在
        """
        pass
    
    def normalize_query(self, query: str) -> str:
        """
        标准化查询语句（转换占位符）
        
        默认实现：如果适配器使用 '?'，将 '%s' 转换为 '?'
        如果适配器使用 '%s'，保持不变
        
        Args:
            query: 原始查询语句（可能包含 '%s' 占位符）
            
        Returns:
            标准化后的查询语句
        """
        placeholder = self.get_placeholder()
        if placeholder == '?':
            # SQLite 使用 ?，需要转换 %s -> ?
            return query.replace("%s", "?")
        else:
            # PostgreSQL/MySQL 使用 %s，保持不变
            return query
    
    def is_initialized(self) -> bool:
        """
        检查适配器是否已初始化
        
        Returns:
            是否已初始化
        """
        return hasattr(self, '_initialized') and self._initialized
