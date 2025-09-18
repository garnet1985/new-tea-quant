#!/usr/bin/env python3
"""
通用数据库连接池 - 解决多进程MySQL连接问题
这是一个基础设施组件，可以被任何需要数据库连接的地方使用
"""
import threading
import queue
import time
from typing import Optional, Dict, Any
from loguru import logger
import pymysql
from .db_config import DB_CONFIG


class ConnectionPool:
    """MySQL连接池 - 多进程安全，支持进程级别连接管理"""
    
    def __init__(self, max_connections: int = 10, is_verbose: bool = False):
        """
        初始化连接池
        
        Args:
            max_connections: 最大连接数
            is_verbose: 是否启用详细日志
        """
        self.max_connections = max_connections
        self.is_verbose = is_verbose
        self._pool = queue.Queue(maxsize=max_connections)
        self._lock = threading.Lock()
        self._created_connections = 0
        self._config = DB_CONFIG['base']
        
        # 进程级别连接跟踪
        self._used_connections = set()  # 跟踪已使用的连接 (process_id, conn)
        self._process_connections = {}  # 进程ID -> 连接列表
        
        # 预创建连接
        self._initialize_pool()
    
    def _initialize_pool(self):
        """初始化连接池"""
        if self.is_verbose:
            logger.info(f"初始化MySQL连接池，最大连接数: {self.max_connections}")
        
        for _ in range(min(4, self.max_connections)):  # 预创建4个连接
            conn = self._create_connection()
            if conn:
                self._pool.put(conn)
    
    def _create_connection(self) -> Optional[pymysql.Connection]:
        """创建新的数据库连接"""
        try:
            conn = pymysql.connect(
                host=self._config['host'],
                port=self._config['port'],
                user=self._config['user'],
                password=self._config['password'],
                database=self._config['database'],
                charset=self._config['charset'],
                autocommit=self._config['autocommit'],
                connect_timeout=10,
                read_timeout=30,
                write_timeout=30
            )
            
            with self._lock:
                self._created_connections += 1
            
            if self.is_verbose:
                logger.debug(f"创建数据库连接 #{self._created_connections}")
            
            return conn
            
        except Exception as e:
            logger.error(f"创建数据库连接失败: {e}")
            return None
    
    def get_connection(self, timeout: float = 5.0) -> Optional[pymysql.Connection]:
        """
        获取数据库连接
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            pymysql.Connection: 数据库连接，失败时返回None
        """
        try:
            # 尝试从池中获取连接
            conn = self._pool.get(timeout=timeout)
            
            # 检查连接是否有效
            if self._is_connection_valid(conn):
                return conn
            else:
                # 连接无效，关闭并创建新连接
                self._close_connection(conn)
                return self._create_connection()
                
        except queue.Empty:
            # 池中没有可用连接，尝试创建新连接
            if self._created_connections < self.max_connections:
                return self._create_connection()
            else:
                logger.warning("连接池已满，无法获取连接")
                return None
        except Exception as e:
            logger.error(f"获取数据库连接失败: {e}")
            return None
    
    def return_connection(self, conn: pymysql.Connection):
        """
        归还数据库连接到池中
        
        Args:
            conn: 数据库连接
        """
        if conn and self._is_connection_valid(conn):
            try:
                self._pool.put_nowait(conn)
            except queue.Full:
                # 池已满，关闭连接
                self._close_connection(conn)
        else:
            # 连接无效，关闭连接
            self._close_connection(conn)
    
    def get_connection_for_process(self, process_id: str, timeout: float = 5.0) -> Optional[pymysql.Connection]:
        """
        为进程分配连接
        
        Args:
            process_id: 进程ID
            timeout: 超时时间（秒）
            
        Returns:
            pymysql.Connection: 数据库连接，失败时返回None
        """
        try:
            # 获取连接
            conn = self.get_connection(timeout)
            if conn:
                # 跟踪连接使用
                with self._lock:
                    self._used_connections.add((process_id, conn))
                    if process_id not in self._process_connections:
                        self._process_connections[process_id] = []
                    self._process_connections[process_id].append(conn)
                
                if self.is_verbose:
                    logger.debug(f"进程 {process_id} 获取连接: {id(conn)}")
                
                return conn
            else:
                logger.error(f"进程 {process_id} 无法获取连接")
                return None
                
        except Exception as e:
            logger.error(f"进程 {process_id} 获取连接失败: {e}")
            return None
    
    def return_connection_from_process(self, process_id: str, conn: pymysql.Connection):
        """
        回收进程连接
        
        Args:
            process_id: 进程ID
            conn: 数据库连接
        """
        try:
            # 从跟踪中移除
            with self._lock:
                self._used_connections.discard((process_id, conn))
                if process_id in self._process_connections:
                    self._process_connections[process_id].remove(conn)
                    if not self._process_connections[process_id]:
                        del self._process_connections[process_id]
            
            # 归还连接
            self.return_connection(conn)
            
            if self.is_verbose:
                logger.debug(f"进程 {process_id} 归还连接: {id(conn)}")
                
        except Exception as e:
            logger.error(f"进程 {process_id} 归还连接失败: {e}")
    
    def cleanup_process_connections(self, process_id: str):
        """
        清理进程的所有连接
        
        Args:
            process_id: 进程ID
        """
        try:
            with self._lock:
                if process_id in self._process_connections:
                    connections = self._process_connections[process_id].copy()
                    del self._process_connections[process_id]
                else:
                    connections = []
            
            # 归还所有连接
            for conn in connections:
                self._used_connections.discard((process_id, conn))
                self.return_connection(conn)
            
            if self.is_verbose and connections:
                logger.info(f"清理进程 {process_id} 的 {len(connections)} 个连接")
                
        except Exception as e:
            logger.error(f"清理进程 {process_id} 连接失败: {e}")
    
    def get_process_stats(self) -> Dict[str, Any]:
        """
        获取进程连接统计信息
        
        Returns:
            Dict: 统计信息
        """
        with self._lock:
            return {
                'total_connections': self._created_connections,
                'available_connections': self._pool.qsize(),
                'used_connections': len(self._used_connections),
                'process_count': len(self._process_connections),
                'max_connections': self.max_connections
            }
    
    def _is_connection_valid(self, conn: pymysql.Connection) -> bool:
        """检查连接是否有效"""
        try:
            if conn is None:
                return False
            
            # 执行简单查询测试连接
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return True
            
        except Exception:
            return False
    
    def _close_connection(self, conn: pymysql.Connection):
        """关闭数据库连接"""
        try:
            if conn:
                conn.close()
                with self._lock:
                    self._created_connections -= 1
        except Exception as e:
            logger.error(f"关闭数据库连接失败: {e}")
    
    def close_all(self):
        """关闭所有连接"""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                self._close_connection(conn)
            except queue.Empty:
                break
        
        if self.is_verbose:
            logger.info("连接池已关闭")


# 全局连接池实例
_global_pool: Optional[ConnectionPool] = None
_pool_lock = threading.Lock()


def get_connection_pool() -> ConnectionPool:
    """获取全局连接池实例"""
    global _global_pool
    
    if _global_pool is None:
        with _pool_lock:
            if _global_pool is None:
                _global_pool = ConnectionPool(max_connections=20, is_verbose=True)
    
    return _global_pool


def get_connection(timeout: float = 5.0) -> Optional[pymysql.Connection]:
    """获取数据库连接"""
    pool = get_connection_pool()
    return pool.get_connection(timeout)


def return_connection(conn: pymysql.Connection):
    """归还数据库连接"""
    pool = get_connection_pool()
    pool.return_connection(conn)


def get_connection_for_process(process_id: str, timeout: float = 5.0) -> Optional[pymysql.Connection]:
    """为进程获取数据库连接"""
    pool = get_connection_pool()
    return pool.get_connection_for_process(process_id, timeout)


def return_connection_from_process(process_id: str, conn: pymysql.Connection):
    """回收进程的数据库连接"""
    pool = get_connection_pool()
    pool.return_connection_from_process(process_id, conn)


def cleanup_process_connections(process_id: str):
    """清理进程的所有连接"""
    pool = get_connection_pool()
    pool.cleanup_process_connections(process_id)


def get_process_stats() -> Dict[str, Any]:
    """获取进程连接统计信息"""
    pool = get_connection_pool()
    return pool.get_process_stats()
