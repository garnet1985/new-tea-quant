"""
DatabaseManager - 简化的 MySQL 数据库管理器
- 使用 DBUtils 管理连接池（自动扩容、健康检查）
- 使用 DbSchemaManager 管理表结构
- 提供简洁的 CRUD 接口
"""
import pymysql
from typing import Optional, Dict, List, Any, Callable
from contextlib import contextmanager
from loguru import logger
from dbutils.pooled_db import PooledDB

from .db_config_manager import DB_CONFIG
from .db_schema_manager import DbSchemaManager


class DatabaseManager:
    """
    简化的数据库管理器
    
    职责：
    - 连接池管理（使用 DBUtils）
    - 基础 CRUD 操作
    - 事务管理
    - 提供默认实例（支持多进程自动初始化）
    
    不再负责：
    - Schema 解析和建表（由 SchemaManager 负责）
    - 表模型缓存（归 DataManager）
    - 异步操作
    - 写入队列
    """
    
    _default_instance = None  # 默认实例（支持多进程）
    _auto_init_enabled = True  # 是否启用自动初始化
    
    def __init__(self, config: Dict = None, is_verbose: bool = False):
        """
        初始化数据库管理器
        
        Args:
            config: 数据库配置（默认使用 DB_CONFIG）
            is_verbose: 是否输出详细日志
        """
        self.config = config or DB_CONFIG
        self.is_verbose = is_verbose
        self.pool = None
        self._initialized = False
        
        # Schema 管理器
        self.schema_manager = DbSchemaManager(
            charset=self.config['base']['charset'],
            is_verbose=is_verbose
        )
    
    @classmethod
    def set_default(cls, instance: 'DatabaseManager'):
        """
        设置默认的 DatabaseManager 实例
        
        Args:
            instance: DatabaseManager 实例
        """
        cls._default_instance = instance
        if instance.is_verbose:
            logger.info("✅ DatabaseManager 已设置为默认实例")
    
    @classmethod
    def get_default(cls, auto_init: bool = True) -> 'DatabaseManager':
        """
        获取默认的 DatabaseManager 实例
        
        多进程安全：
        - 如果实例不存在（多进程场景下 context 丢失）
        - 会自动创建并初始化新实例
        
        Args:
            auto_init: 是否自动初始化（默认 True）
        
        Returns:
            DatabaseManager 实例
        """
        if cls._default_instance is None:
            if auto_init and cls._auto_init_enabled:
                # 自动创建并初始化（多进程场景）
                logger.info("🔄 检测到 DatabaseManager 未初始化（可能是多进程场景），自动创建实例")
                instance = cls(is_verbose=False)
                instance.initialize()
                cls._default_instance = instance
                logger.info("✅ DatabaseManager 自动初始化完成")
            else:
                raise RuntimeError(
                    "No default DatabaseManager instance. "
                    "Call DatabaseManager.set_default(db) or enable auto_init."
                )
        
        return cls._default_instance
    
    @classmethod
    def reset_default(cls):
        """
        重置默认实例
        
        使用场景：
        - 测试时清理状态
        - 切换数据库配置
        """
        if cls._default_instance is not None:
            # 关闭连接池
            if hasattr(cls._default_instance, 'pool') and cls._default_instance.pool:
                cls._default_instance.pool.close()
        cls._default_instance = None
        logger.info("🔄 DatabaseManager 默认实例已重置")
    
    @classmethod
    def set_default(cls, instance: 'DatabaseManager'):
        """
        设置默认的 DatabaseManager 实例
        
        Args:
            instance: DatabaseManager 实例
        """
        cls._default_instance = instance
    
    @classmethod
    def get_default(cls) -> 'DatabaseManager':
        """
        获取默认的 DatabaseManager 实例
        
        如果实例不存在（如多进程场景），会自动创建并初始化
        
        Returns:
            DatabaseManager 实例
        """
        if cls._default_instance is None:
            if cls._auto_init_enabled:
                # 自动创建并初始化（多进程场景）
                logger.info("🔄 检测到 DatabaseManager 未初始化（可能是多进程场景），自动创建实例")
                instance = cls(is_verbose=False)
                instance.initialize()
                cls._default_instance = instance
            else:
                raise RuntimeError(
                    "No default DatabaseManager instance. "
                    "Call DatabaseManager.set_default(db) first."
                )
        
        return cls._default_instance
    
    @classmethod
    def reset_default(cls):
        """
        重置默认实例（主要用于测试）
        """
        cls._default_instance = None

    def initialize(self):
        """
        初始化数据库管理器（仅基础设施）
        
        步骤：
        1. 创建数据库（如果不存在）
        2. 初始化连接池
        
        注意：不再创建表，表的创建由 DataManager 负责
        """
        try:
            # 1. 确保数据库存在
            self._ensure_database_exists()
            
            # 2. 初始化连接池
            self._init_connection_pool()
            
            self._initialized = True
            
            if self.is_verbose:
                logger.info("✅ DatabaseManager 初始化完成（连接池已就绪）")
                
        except Exception as e:
            logger.error(f"❌ DatabaseManager 初始化失败: {e}")
            raise
    
    def _ensure_database_exists(self):
        """确保数据库存在，不存在则创建"""
        try:
            # 先不指定数据库，连接到 MySQL
            temp_conn = pymysql.connect(
                host=self.config['base']['host'],
                user=self.config['base']['user'],
                password=self.config['base']['password'],
                port=self.config['base']['port'],
                charset=self.config['base']['charset']
            )
            
            try:
                with temp_conn.cursor() as cursor:
                    db_name = self.config['base']['database']
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET {self.config['base']['charset']}")
                    if self.is_verbose:
                        logger.info(f"✅ 数据库 {db_name} 已就绪")
            finally:
                temp_conn.close()
                
        except Exception as e:
            logger.error(f"❌ 创建数据库失败: {e}")
            raise
    
    def _init_connection_pool(self):
        """
        初始化连接池（使用 DBUtils）
        
        特性：
        - 自动扩容（从 min 到 max）
        - 自动健康检查（ping=1）
        - 线程安全
        - 连接复用
        """
        try:
            pool_config = self.config.get('pool', {})
            timeout_config = self.config.get('timeout', {})
            
            self.pool = PooledDB(
                creator=pymysql,
                
                # 连接池配置
                maxconnections=pool_config.get('pool_size_max', 30),  # 最大连接数
                mincached=pool_config.get('pool_size_min', 5),        # 最小空闲连接
                maxcached=10,                                          # 最大空闲连接
                maxshared=0,                                           # 最大共享连接（0=不共享）
                blocking=True,                                         # 连接用完时阻塞等待
                maxusage=None,                                         # 连接最大使用次数（None=无限制）
                
                # 健康检查
                ping=1,  # 0=不检查, 1=默认检查, 2=事务开始时检查, 4=执行查询时检查, 7=总是检查
                
                # 数据库连接参数
                host=self.config['base']['host'],
                user=self.config['base']['user'],
                password=self.config['base']['password'],
                database=self.config['base']['database'],
                port=self.config['base']['port'],
                charset=self.config['base']['charset'],
                
                # 超时配置
                connect_timeout=timeout_config.get('connection', 60),
                read_timeout=timeout_config.get('read', 60),
                write_timeout=timeout_config.get('write', 60),
                
                # 其他配置
                autocommit=self.config['base'].get('autocommit', True),
                cursorclass=pymysql.cursors.DictCursor,  # 返回字典格式
            )
            
            if self.is_verbose:
                logger.info(f"✅ 连接池初始化完成（最小: {pool_config.get('pool_size_min', 5)}, 最大: {pool_config.get('pool_size_max', 30)}）")
            
        except Exception as e:
            logger.error(f"❌ 连接池初始化失败: {e}")
            raise
    
    # ==================== 连接管理 ====================
    
    @contextmanager
    def get_connection(self):
        """
        获取数据库连接（上下文管理器）
        
        使用方式:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(...)
        """
        if not self.pool:
            raise RuntimeError("连接池未初始化，请先调用 initialize()")
        
        conn = self.pool.connection()
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()  # DBUtils 会自动归还到池中
    
    @contextmanager
    def transaction(self):
        """
        事务上下文管理器
        
        使用方式:
            with db.transaction() as cursor:
                cursor.execute("INSERT ...")
                cursor.execute("UPDATE ...")
                # 自动提交或回滚
        """
        with self.get_connection() as conn:
            # 临时关闭自动提交
            old_autocommit = conn.get_autocommit()
            conn.autocommit(False)
            
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise
            finally:
                cursor.close()
                conn.autocommit(old_autocommit)
    
    # ==================== 表管理（委托给 SchemaManager）====================
    
    def register_table(self, table_name: str, schema: Dict):
        """
        注册自定义表（给策略用）
        
        Args:
            table_name: 表名
            schema: 表的 schema 定义
        """
        self.schema_manager.register_table(table_name, schema)
        
        if self._initialized:
            # 如果已经初始化，立即创建表
            self.schema_manager.create_table_with_indexes(schema, self.get_connection)
    
    def create_registered_tables(self):
        """创建所有注册的表（策略表）"""
        self.schema_manager.create_registered_tables(self.get_connection)
    
    def is_table_exists(self, table_name: str) -> bool:
        """
        检查表是否存在
        
        Args:
            table_name: 表名
            
        Returns:
            是否存在
        """
        return self.schema_manager.is_table_exists(
            table_name, 
            self.config['base']['database'], 
            self.get_connection()
        )
    
    def get_table_schema(self, table_name: str) -> Optional[Dict]:
        """
        获取表的 schema
        
        Args:
            table_name: 表名
            
        Returns:
            schema 字典，不存在返回 None
        """
        return self.schema_manager.get_table_schema(table_name)
    
    def get_table_fields(self, table_name: str) -> List[str]:
        """
        获取表的所有字段名
        
        Args:
            table_name: 表名
            
        Returns:
            字段名列表
        """
        return self.schema_manager.get_table_fields(table_name)
    
    # ==================== 工具方法 ====================
    
    def close(self):
        """关闭连接池"""
        if self.pool:
            self.pool.close()
            self.pool = None
            if self.is_verbose:
                logger.info("✅ 连接池已关闭")
    
    def get_stats(self) -> Dict:
        """
        获取连接池统计信息
        
        Returns:
            统计信息字典
        """
        if not self.pool:
            return {}
        
        pool_config = self.config.get('pool', {})
        return {
            'initialized': self._initialized,
            'max_connections': pool_config.get('pool_size_max', 30),
            'min_cached': pool_config.get('pool_size_min', 5),
        }
    
    @contextmanager
    def get_sync_cursor(self):
        """
        获取数据库游标的上下文管理器
        
        使用方式:
            with db.get_sync_cursor() as cursor:
                cursor.execute("SELECT * FROM table")
                results = cursor.fetchall()
        """
        if not self._initialized:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")
        
        connection = self.pool.connection()
        cursor = None
        
        try:
            cursor = connection.cursor(pymysql.cursors.DictCursor)
            yield cursor
            connection.commit()
        except Exception as e:
            connection.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            connection.close()
    
    def execute_sync_query(self, query: str, params: Any = None) -> List[Dict[str, Any]]:
        """
        执行同步查询语句
        
        Args:
            query: SQL 查询语句
            params: 查询参数
            
        Returns:
            查询结果列表
        """
        with self.get_sync_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def queue_write(self, table_name: str, data_list: List[Dict], unique_keys: List[str], callback: Callable = None):
        """
        队列写入（兼容方法）
        
        由于新的 DatabaseManager 使用 DBUtils 管理连接，
        队列写入已集成到连接池，此方法直接执行写入
        
        Args:
            table_name: 表名
            data_list: 数据列表
            unique_keys: 唯一键
            callback: 回调函数
        """
        try:
            # 直接执行批量插入/更新
            from .db_base_model import DBService
            
            if not data_list:
                return
        
            columns, values, update_clause = DBService.to_upsert_params(data_list, unique_keys)
            query = f"""
                INSERT INTO {table_name} ({', '.join(columns)}) 
                VALUES ({', '.join(['%s'] * len(columns))})
                ON DUPLICATE KEY UPDATE {update_clause}
            """
            
            with self.get_sync_cursor() as cursor:
                cursor.executemany(query, values)
            
            if callback:
                callback(table_name, len(data_list))
                    
        except Exception as e:
            logger.error(f"Failed to write to {table_name}: {e}")
            raise
    
    def wait_for_writes(self, timeout: float = 30.0):
        """
        等待所有写入完成（兼容方法）
        
        新的 DatabaseManager 使用同步写入，此方法立即返回
        """
        pass
    
    def __del__(self):
        """析构函数：确保连接池关闭"""
        try:
            self.close()
        except:
            pass
