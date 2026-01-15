"""
DatabaseAdapterFactory - 数据库适配器工厂

根据配置创建相应的数据库适配器。
支持：PostgreSQL、MySQL、SQLite
"""
from typing import Dict, Any, Optional
from loguru import logger

from .base_adapter import BaseDatabaseAdapter
from .postgresql_adapter import PostgreSQLAdapter
from .mysql_adapter import MySQLAdapter
from .sqlite_adapter import SQLiteAdapter


class DatabaseAdapterFactory:
    """
    数据库适配器工厂
    
    根据配置自动创建相应的数据库适配器。
    """
    
    @staticmethod
    def create(config: Dict[str, Any], is_verbose: bool = False, read_only: bool = False) -> BaseDatabaseAdapter:
        """
        创建数据库适配器
        
        Args:
            config: 数据库配置字典
                必须包含 'database_type' 字段（'postgresql', 'mysql', 'sqlite'）
                以及对应的数据库配置
            is_verbose: 是否输出详细日志
            read_only: 是否以只读模式打开（仅 SQLite 支持）
            
        Returns:
            数据库适配器实例
            
        Example:
            # PostgreSQL 配置
            config = {
                'database_type': 'postgresql',
                'postgresql': {
                    'host': 'localhost',
                    'port': 5432,
                    'database': 'stocks_py',
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
                    'database': 'stocks_py',
                    'user': 'root',
                    'password': 'password'
                }
            }
            
            # SQLite 配置
            config = {
                'database_type': 'sqlite',
                'sqlite': {
                    'db_path': 'data/stocks.db'
                }
            }
        """
        database_type = config.get('database_type', 'postgresql').lower()
        
        if database_type == 'postgresql':
            pg_config = config.get('postgresql')
            if not pg_config:
                raise ValueError("PostgreSQL 配置缺失，请提供 'postgresql' 配置项")
            
            adapter = PostgreSQLAdapter(pg_config, is_verbose=is_verbose)
            adapter.connect()
            return adapter
            
        elif database_type == 'mysql':
            mysql_config = config.get('mysql')
            if not mysql_config:
                raise ValueError("MySQL 配置缺失，请提供 'mysql' 配置项")
            
            adapter = MySQLAdapter(mysql_config, is_verbose=is_verbose)
            adapter.connect()
            return adapter
            
        elif database_type == 'sqlite':
            sqlite_config = config.get('sqlite')
            if not sqlite_config:
                raise ValueError("SQLite 配置缺失，请提供 'sqlite' 配置项")
            
            adapter = SQLiteAdapter(sqlite_config, is_verbose=is_verbose, read_only=read_only)
            adapter.connect()
            return adapter
            
        else:
            raise ValueError(f"不支持的数据库类型: {database_type}，支持的类型: 'postgresql', 'mysql', 'sqlite'")
    
    @staticmethod
    def create_from_legacy_config(
        config: Dict[str, Any],
        is_verbose: bool = False,
        read_only: bool = False
    ) -> BaseDatabaseAdapter:
        """
        从旧版配置创建适配器（向后兼容）
        
        如果配置中没有 'database_type'，自动检测：
        - 如果有 'db_path'，使用 SQLite
        - 如果有 'host' 和 'database'，根据端口判断：
          - port 3306 或未指定 → MySQL
          - port 5432 → PostgreSQL
        
        Args:
            config: 数据库配置字典
            is_verbose: 是否输出详细日志
            read_only: 是否以只读模式打开（仅 SQLite 支持）
            
        Returns:
            数据库适配器实例
        """
        # 检查是否已有 database_type
        if 'database_type' in config:
            return DatabaseAdapterFactory.create(config, is_verbose, read_only)
        
        # 自动检测
        if 'db_path' in config:
            # SQLite 配置
            logger.info("🔍 自动检测到 SQLite 配置")
            return DatabaseAdapterFactory.create({
                'database_type': 'sqlite',
                'sqlite': config
            }, is_verbose, read_only)
        
        elif 'host' in config and 'database' in config:
            # 根据端口判断是 MySQL 还是 PostgreSQL
            port = config.get('port', 3306)
            if port == 5432:
                logger.info("🔍 自动检测到 PostgreSQL 配置")
                return DatabaseAdapterFactory.create({
                    'database_type': 'postgresql',
                    'postgresql': config
                }, is_verbose, read_only)
            else:
                logger.info("🔍 自动检测到 MySQL 配置")
                return DatabaseAdapterFactory.create({
                    'database_type': 'mysql',
                    'mysql': config
                }, is_verbose, read_only)
        
        else:
            raise ValueError("无法自动检测数据库类型，请明确指定 'database_type' 或提供 'db_path'（SQLite）或 'host'+'database'（MySQL/PostgreSQL）")
