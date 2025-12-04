#!/usr/bin/env python3
"""
多进程安全的数据库管理器 - 使用通用连接池解决MySQL多进程问题
"""
import threading
import time
from typing import Optional, Dict, Any
from loguru import logger
from .connection_pool import get_connection, return_connection
from .db_model import BaseTableModel


class ProcessSafeDatabaseManager:
    """多进程安全的数据库管理器 - 使用通用连接池"""
    
    def __init__(self, is_verbose: bool = False):
        """
        初始化多进程安全的数据库管理器
        
        Args:
            is_verbose: 是否启用详细日志
        """
        self.is_verbose = is_verbose
        self.tables = {}
        self.registered_tables = {}
        self._tables_lock = threading.Lock()
        
        if self.is_verbose:
            logger.info("初始化多进程安全的数据库管理器（使用通用连接池）")
    
    def initialize(self):
        """初始化数据库管理器"""
        if self.is_verbose:
            logger.info("多进程安全数据库管理器初始化完成")
    
    def get_connection(self):
        """获取数据库连接（从通用连接池）"""
        return get_connection()
    
    def return_connection(self, conn):
        """归还数据库连接（到通用连接池）"""
        return_connection(conn)
    
    def execute_query(self, sql: str, params: tuple = None) -> list:
        """
        执行查询SQL
        
        Args:
            sql: SQL语句
            params: 参数元组
            
        Returns:
            list: 查询结果
        """
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                raise Exception("无法获取数据库连接")
            
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"执行查询失败: {sql}, 错误: {e}")
            raise
        finally:
            if conn:
                self.return_connection(conn)
    
    def execute_update(self, sql: str, params: tuple = None) -> int:
        """
        执行更新SQL
        
        Args:
            sql: SQL语句
            params: 参数元组
            
        Returns:
            int: 影响的行数
        """
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                raise Exception("无法获取数据库连接")
            
            with conn.cursor() as cursor:
                affected_rows = cursor.execute(sql, params)
                conn.commit()
                return affected_rows
                
        except Exception as e:
            logger.error(f"执行更新失败: {sql}, 错误: {e}")
            raise
        finally:
            if conn:
                self.return_connection(conn)
    
    def register_table(self, table_name: str, table_class: type):
        """
        注册表类
        
        Args:
            table_name: 表名
            table_class: 表类
        """
        with self._tables_lock:
            self.registered_tables[table_name] = table_class
            if self.is_verbose:
                logger.info(f"注册表: {table_name}")
    
    def get_table(self, table_name: str) -> Optional[BaseTableModel]:
        """
        获取表实例
        
        Args:
            table_name: 表名
            
        Returns:
            DatabaseModel: 表实例
        """
        with self._tables_lock:
            if table_name not in self.tables:
                if table_name in self.registered_tables:
                    table_class = self.registered_tables[table_name]
                    self.tables[table_name] = table_class(self)
                else:
                    logger.warning(f"表 {table_name} 未注册")
                    return None
            
            return self.tables[table_name]
    
    def create_tables(self):
        """创建所有注册的表"""
        with self._tables_lock:
            for table_name, table_class in self.registered_tables.items():
                if table_name not in self.tables:
                    self.tables[table_name] = table_class(self)
                
                # 创建表结构
                try:
                    self.tables[table_name].create_table()
                    if self.is_verbose:
                        logger.info(f"创建表: {table_name}")
                except Exception as e:
                    logger.error(f"创建表 {table_name} 失败: {e}")
    
    def get_table_instance(self, table_name: str) -> Optional[BaseTableModel]:
        """
        获取表实例（兼容性方法）
        
        Args:
            table_name: 表名
            
        Returns:
            BaseTableModel: 表实例
        """
        return self.get_table(table_name)
