"""
DatabaseAdapterFactory - 数据库适配器工厂

根据配置创建相应的数据库适配器。
支持：PostgreSQL、MySQL
"""
from typing import Dict, Any, Optional
import logging

from .base_adapter import BaseDatabaseAdapter

logger = logging.getLogger(__name__)


class DatabaseAdapterFactory:
    """
    数据库适配器工厂
    
    根据配置自动创建相应的数据库适配器。
    """
    
    @staticmethod
    def create(config: Dict[str, Any], is_verbose: bool = False) -> BaseDatabaseAdapter:
        """
        创建数据库适配器
        
        Args:
            config: 数据库配置字典
                必须包含 'database_type' 字段（'postgresql', 'mysql'）
                以及对应的数据库配置
            is_verbose: 是否输出详细日志
            
        Returns:
            数据库适配器实例
            
        Example:
            # PostgreSQL 配置
            config = {
                'database_type': 'postgresql',
                'postgresql': {
                    'host': 'localhost',
                    'port': 5432,
                    'database': 'new_tea_quant',
                    'user': 'postgres',
                    'password': 'password'
                }
            }
            
            # MySQL 配置
            config = {
                'database_type': 'mysql',
                'mysql': {
                    'host': 'localhost',
                    'port': 3306,
                    'database': 'new_tea_quant',
                    'user': 'root',
                    'password': 'password'
                }
            }
        """
        database_type = config.get('database_type', 'postgresql').lower()
        
        if database_type == 'postgresql':
            from .postgresql_adapter import PostgreSQLAdapter

            pg_config = config.get('postgresql')
            if not pg_config:
                raise ValueError("PostgreSQL 配置缺失，请提供 'postgresql' 配置项")
            
            adapter = PostgreSQLAdapter(pg_config, is_verbose=is_verbose)
            adapter.connect()
            return adapter
            
        elif database_type == 'mysql':
            from .mysql_adapter import MySQLAdapter

            mysql_config = config.get('mysql')
            if not mysql_config:
                raise ValueError("MySQL 配置缺失，请提供 'mysql' 配置项")
            
            adapter = MySQLAdapter(mysql_config, is_verbose=is_verbose)
            adapter.connect()
            return adapter
            
        else:
            raise ValueError(f"不支持的数据库类型: {database_type}，支持的类型: 'postgresql', 'mysql'")
