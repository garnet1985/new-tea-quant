#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import pymysql
from loguru import logger
from utils.db.config import DB_CONFIG


class ThreadSafeDBManager:
    """
    线程安全的数据库管理器
    为每个线程提供独立的数据库连接
    """
    
    def __init__(self):
        self.connection_pool = {}
        self.lock = threading.Lock()
        self.db_config = DB_CONFIG
    
    def get_connection(self, thread_id=None):
        """
        获取线程专用的数据库连接
        
        Args:
            thread_id: 线程ID，如果为None则使用当前线程ID
            
        Returns:
            pymysql.Connection: 数据库连接
        """
        if thread_id is None:
            thread_id = threading.get_ident()
        
        if thread_id not in self.connection_pool:
            with self.lock:
                if thread_id not in self.connection_pool:
                    try:
                        connection = self._create_connection()
                        self.connection_pool[thread_id] = connection
                        logger.debug(f"为线程 {thread_id} 创建新的数据库连接")
                    except Exception as e:
                        logger.error(f"为线程 {thread_id} 创建数据库连接失败: {e}")
                        raise
        else:
            # 检查连接是否还有效
            connection = self.connection_pool[thread_id]
            try:
                connection.ping(reconnect=True)
            except Exception as e:
                logger.warning(f"线程 {thread_id} 的数据库连接已断开，重新创建: {e}")
                with self.lock:
                    try:
                        connection.close()
                    except:
                        pass
                    connection = self._create_connection()
                    self.connection_pool[thread_id] = connection
        
        return self.connection_pool[thread_id]
    
    def _create_connection(self):
        """创建新的数据库连接"""
        try:
            # 从嵌套配置中获取数据库配置
            db_config = self.db_config['base']
            connection = pymysql.connect(
                host=db_config['host'],
                port=db_config['port'],
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'],
                charset=db_config['charset'],
                autocommit=True,
                cursorclass=pymysql.cursors.DictCursor
            )
            return connection
        except Exception as e:
            logger.error(f"创建数据库连接失败: {e}")
            raise
    
    def get_cursor(self, thread_id=None):
        """
        获取线程专用的数据库游标
        
        Args:
            thread_id: 线程ID
            
        Returns:
            pymysql.cursors.DictCursor: 数据库游标
        """
        connection = self.get_connection(thread_id)
        return connection.cursor()
    
    def execute_query(self, sql, params=None, thread_id=None):
        """
        执行查询语句
        
        Args:
            sql: SQL语句
            params: 参数
            thread_id: 线程ID
            
        Returns:
            list: 查询结果
        """
        cursor = self.get_cursor(thread_id)
        try:
            cursor.execute(sql, params)
            result = cursor.fetchall()
            return result
        except Exception as e:
            logger.error(f"执行查询失败: {e}, SQL: {sql}, 参数: {params}")
            raise
        finally:
            cursor.close()
    
    def execute_update(self, sql, params=None, thread_id=None):
        """
        执行更新语句
        
        Args:
            sql: SQL语句
            params: 参数
            thread_id: 线程ID
            
        Returns:
            int: 影响的行数
        """
        cursor = self.get_cursor(thread_id)
        try:
            affected_rows = cursor.execute(sql, params)
            return affected_rows
        except Exception as e:
            logger.error(f"执行更新失败: {e}, SQL: {sql}, 参数: {params}")
            raise
        finally:
            cursor.close()
    
    def close_connection(self, thread_id=None):
        """
        关闭指定线程的数据库连接
        
        Args:
            thread_id: 线程ID，如果为None则关闭当前线程的连接
        """
        if thread_id is None:
            thread_id = threading.get_ident()
        
        with self.lock:
            if thread_id in self.connection_pool:
                try:
                    self.connection_pool[thread_id].close()
                    del self.connection_pool[thread_id]
                    logger.debug(f"关闭线程 {thread_id} 的数据库连接")
                except Exception as e:
                    logger.warning(f"关闭线程 {thread_id} 的数据库连接时出错: {e}")
    
    def close_all_connections(self):
        """关闭所有数据库连接"""
        with self.lock:
            for thread_id, connection in self.connection_pool.items():
                try:
                    connection.close()
                    logger.debug(f"关闭线程 {thread_id} 的数据库连接")
                except Exception as e:
                    logger.warning(f"关闭线程 {thread_id} 的数据库连接时出错: {e}")
            self.connection_pool.clear()
    
    def __del__(self):
        """析构函数，确保关闭所有连接"""
        self.close_all_connections()


# 全局线程安全数据库管理器实例
_thread_safe_db_manager = None
_thread_safe_db_manager_lock = threading.Lock()


def get_thread_safe_db_manager():
    """获取全局线程安全数据库管理器实例"""
    global _thread_safe_db_manager
    if _thread_safe_db_manager is None:
        with _thread_safe_db_manager_lock:
            if _thread_safe_db_manager is None:
                _thread_safe_db_manager = ThreadSafeDBManager()
    return _thread_safe_db_manager 