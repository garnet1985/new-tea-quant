"""
DatabaseManager - DuckDB 数据库管理器
- 使用 DuckDB 单文件数据库
- 使用 DbSchemaManager 管理表结构
- 提供简洁的 CRUD 接口
"""
import duckdb
from typing import Optional, Dict, List, Any, Callable
from contextlib import contextmanager
from pathlib import Path
from loguru import logger
from datetime import datetime, date

from app.core.conf.db_conf import DUCKDB_CONF
from app.core.infra.db.batch_write_queue import BatchWriteQueue
from .db_schema_manager import DbSchemaManager


class DuckDBCursor:
    """
    DuckDB 游标包装类
    """
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn
        self._result = None
        self._description = None
        self._cursor = None
    
    def execute(self, query: str, params: Any = None):
        """执行 SQL 查询"""
        # DuckDB 使用 ? 作为占位符，统一转换 %s -> ?
        query = query.replace("%s", "?")
        
        # DuckDB 的 execute 返回一个结果对象
        if params:
            self._cursor = self.conn.execute(query, params)
        else:
            self._cursor = self.conn.execute(query)
        
        # 获取列信息
        try:
            # DuckDB 的 description 是列名列表
            if hasattr(self._cursor, 'description'):
                self._description = [col[0] for col in self._cursor.description]
            else:
                # 尝试从结果推断
                self._result = self._cursor.fetchall()
                if self._result and isinstance(self._result[0], dict):
                    self._description = list(self._result[0].keys())
                elif self._result:
                    # 如果是元组，需要从 cursor 获取列名
                    # DuckDB 的 fetchall() 可能返回字典或元组
                    pass
        except:
            self._description = []
        
        return self
    
    def fetchall(self) -> List[Dict[str, Any]]:
        """获取所有结果，转换为字典列表"""
        if self._cursor is None:
            return []
        
        try:
            # DuckDB 的 fetchall() 可能返回字典列表或元组列表
            result = self._cursor.fetchall()
            
            if not result:
                return []
            
            # 如果已经是字典列表，直接返回
            if isinstance(result[0], dict):
                return list(result)
            
            # 如果是元组列表，需要转换为字典
            if self._description:
                return [dict(zip(self._description, row)) for row in result]
            else:
                # 尝试获取列名
                try:
                    if hasattr(self._cursor, 'description'):
                        columns = [col[0] for col in self._cursor.description]
                        return [dict(zip(columns, row)) for row in result]
                except:
                    pass
                
                # 最后使用数字索引
                return [dict(enumerate(row)) for row in result]
        except Exception as e:
            logger.error(f"fetchall 失败: {e}")
            return []
    
    def fetchone(self) -> Optional[Dict[str, Any]]:
        """获取一条结果"""
        results = self.fetchall()
        return results[0] if results else None
    
    @property
    def rowcount(self) -> int:
        """返回影响的行数"""
        if self._result:
            return len(self._result)
        return 0
    

    def close(self):
        """关闭游标（DuckDB 不需要显式关闭）"""
        pass


class DatabaseManager:
    """
    DuckDB 数据库管理器
    
    职责：
    - DuckDB 连接管理
    - 基础 CRUD 操作
    - 事务管理
    - 提供默认实例（支持多进程自动初始化）
    
    不再负责：
    - Schema 解析和建表（由 SchemaManager 负责）
    - 表模型缓存（归 DataManager）
    - 连接池（DuckDB 单连接即可）
    """
    
    _default_instance = None  # 默认实例（支持多进程）
    _auto_init_enabled = True  # 是否启用自动初始化
    
    def __init__(self, config: Dict = None, is_verbose: bool = False, read_only: bool = False):
        """
        初始化数据库管理器
        
        Args:
            config: 数据库配置（默认使用 DUCKDB_CONF）
            is_verbose: 是否输出详细日志
            read_only: 是否以只读模式打开（多进程读取场景使用）
        """
        self.config = config or DUCKDB_CONF
        self.is_verbose = is_verbose
        self.read_only = read_only
        self.conn: Optional[duckdb.DuckDBPyConnection] = None
        self._initialized = False
        
        # Schema 管理器
        self.schema_manager = DbSchemaManager(
            is_verbose=is_verbose
        )
        
        # 批量写入队列（延迟初始化，在 initialize 后创建）
        self._write_queue = None
        
        # 批量写入队列（延迟初始化，在 initialize 后创建）
        self._write_queue: Optional[BatchWriteQueue] = None
    
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
        - 如果检测到是子进程，自动使用只读模式（避免写锁冲突）
        
        Args:
            auto_init: 是否自动初始化（默认 True）
        
        Returns:
            DatabaseManager 实例
        """
        if cls._default_instance is None:
            if auto_init and cls._auto_init_enabled:
                # 检测是否是子进程（多进程场景）
                import multiprocessing
                is_child_process = multiprocessing.current_process().name != 'MainProcess'
                
                # 自动创建并初始化（多进程场景）
                if is_child_process:
                    logger.info("🔄 检测到子进程环境，自动创建只读 DatabaseManager 实例（避免写锁冲突）")
                    instance = cls(is_verbose=False, read_only=True)
                else:
                    logger.info("🔄 检测到 DatabaseManager 未初始化，自动创建实例")
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
            # 关闭连接
            if hasattr(cls._default_instance, 'conn') and cls._default_instance.conn:
                cls._default_instance.conn.close()
        cls._default_instance = None
        logger.info("🔄 DatabaseManager 默认实例已重置")
    
    def initialize(self):
        """
        初始化数据库管理器
        
        步骤：
        1. 确保数据库文件目录存在
        2. 连接 DuckDB（根据 read_only 参数决定是否只读）
        3. 设置性能参数
        
        注意：不再创建表，表的创建由 DataManager 负责
        """
        try:
            # 1. 确保数据库文件目录存在
            db_path = Path(self.config['db_path'])
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 2. 连接 DuckDB（只读模式允许多进程并发读取）
            if self.read_only:
                self.conn = duckdb.connect(str(db_path), read_only=True)
                if self.is_verbose:
                    logger.info(f"📖 以只读模式连接 DuckDB: {db_path}")
            else:
                self.conn = duckdb.connect(str(db_path))
            
            # 3. 设置性能参数
            threads = self.config.get('threads', 4)
            memory_limit = self.config.get('memory_limit', '8GB')
            
            self.conn.execute(f"SET threads = {threads}")
            self.conn.execute(f"SET memory_limit = '{memory_limit}'")
            
            self._initialized = True
            
            # 初始化批量写入队列（只读模式下跳过）
            if not self.read_only:
                self._init_write_queue()
            elif self.is_verbose:
                logger.info("ℹ️  只读模式，跳过批量写入队列初始化")
            
            if self.is_verbose:
                logger.info(f"✅ DatabaseManager 初始化完成（DuckDB: {db_path}）")
                logger.info(f"   线程数: {threads}, 内存限制: {memory_limit}")
                
        except Exception as e:
            logger.error(f"❌ DatabaseManager 初始化失败: {e}")
            raise
    
    def _init_write_queue(self):
        """初始化批量写入队列"""
        try:
            from .batch_write_queue import BatchWriteQueue
            
            # 从配置读取批量写入参数
            batch_config = self.config.get('batch_write', {})
            batch_size = batch_config.get('batch_size', 1000)
            flush_interval = batch_config.get('flush_interval', 5.0)
            enable = batch_config.get('enable', True)
            
            self._write_queue = BatchWriteQueue(
                db_manager=self,
                batch_size=batch_size,
                flush_interval=flush_interval,
                enable=enable
            )
            
            if self.is_verbose and enable:
                logger.info(f"✅ 批量写入队列已启用 (batch_size={batch_size}, flush_interval={flush_interval}s)")
            elif not enable and self.is_verbose:
                logger.info("ℹ️  批量写入队列已禁用（直接写入模式）")
        except Exception as e:
            logger.warning(f"⚠️ 初始化批量写入队列失败: {e}，将使用直接写入模式")
            self._write_queue = None
    
    # ==================== 连接管理 ====================
    
    @contextmanager
    def get_connection(self):
        """
        获取数据库连接（上下文管理器）
        
        使用方式:
            with db.get_connection() as conn:
                # DuckDB 连接可以直接执行 SQL
                conn.execute("SELECT ...")
        """
        if not self.conn:
            raise RuntimeError("数据库未初始化，请先调用 initialize()")
        
        yield self.conn
    
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
        if not self.conn:
            raise RuntimeError("数据库未初始化，请先调用 initialize()")
        
        # DuckDB 自动管理事务
        cursor = DuckDBCursor(self.conn)
        try:
            yield cursor
            # DuckDB 的 execute 会自动提交
        except Exception as e:
            # 如果出错，DuckDB 会自动回滚
            raise
    
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
        # DuckDB 使用 information_schema
        query = """
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_name = ?
        """
        try:
            result = self.execute_sync_query(query, (table_name,))
            return result[0]['count'] > 0 if result else False
        except Exception as e:
            logger.error(f"检查表是否存在失败: {e}")
            return False
    
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
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self._initialized = False
            if self.is_verbose:
                logger.info("✅ 数据库连接已关闭")
    
    def get_stats(self) -> Dict:
        """
        获取数据库统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'initialized': self._initialized,
            'db_path': str(self.config.get('db_path', '')),
            'threads': self.config.get('threads', 4),
            'memory_limit': self.config.get('memory_limit', '8GB'),
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
        if not self._initialized or not self.conn:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")
        
        cursor = DuckDBCursor(self.conn)
        try:
            yield cursor
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            cursor.close()
    
    def execute_sync_query(self, query: str, params: Any = None) -> List[Dict[str, Any]]:
        """
        执行同步查询语句
        
        Args:
            query: SQL 查询语句（可以使用 %s 占位符，会自动转换为 ?）
            params: 查询参数
            
        Returns:
            查询结果列表（字典格式）
        """
        if not self.conn:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")
        
        # 统一转换占位符：%s -> ?
        query = query.replace("%s", "?")
        
        try:
            # DuckDB 的 execute 返回一个结果对象
            if params:
                cursor = self.conn.execute(query, params)
            else:
                cursor = self.conn.execute(query)
            
            # 获取结果
            result = cursor.fetchall()
            
            # DuckDB 的 fetchall() 可能返回字典列表或元组列表
            if not result:
                return []
            
            # 如果已经是字典列表，直接返回
            if isinstance(result[0], dict):
                return list(result)
            
            # 如果是元组列表，转换为字典
            # 获取列名
            try:
                # DuckDB 的 description 是列信息元组列表
                if hasattr(cursor, 'description') and cursor.description:
                    columns = [col[0] for col in cursor.description]
                    return [dict(zip(columns, row)) for row in result]
            except:
                pass
            
            # 如果获取不到列名，使用数字索引
            return [dict(enumerate(row)) for row in result]
            
        except Exception as e:
            logger.error(f"执行查询失败: {e}\n查询: {query}\n参数: {params}")
            raise
    
    def queue_write(self, table_name: str, data_list: List[Dict], unique_keys: List[str], callback: Callable = None):
        """
        队列写入（使用批量写入队列，解决并发写入问题）
        
        Args:
            table_name: 表名
            data_list: 数据列表
            unique_keys: 唯一键
            callback: 回调函数
        """
        if not data_list:
            return
        
        # 如果批量写入队列可用且启用，使用队列
        if self._write_queue and self._write_queue.enable:
            self._write_queue.enqueue(table_name, data_list, unique_keys, callback)
        else:
            # 否则直接写入（单线程场景或队列未启用）
            self._direct_write(table_name, data_list, unique_keys, callback)
    
    def _direct_write(
        self,
        table_name: str,
        data_list: List[Dict],
        unique_keys: List[str],
        callback: Callable = None
    ):
        """
        直接写入（不使用队列，单线程场景使用）
        
        注意：此方法不是线程安全的，多线程场景应使用 queue_write
        
        Args:
            table_name: 表名
            data_list: 数据列表
            unique_keys: 唯一键列表（如果为空，使用纯 INSERT；否则使用 INSERT ... ON CONFLICT）
            callback: 回调函数
        """
        try:
            from .db_base_model import DBService
            
            if not data_list:
                return
            
            if not unique_keys:
                # 纯 INSERT（不需要去重）
                columns, placeholders = DBService.to_columns_and_values(data_list)
                columns_sql = ', '.join(columns)
                values = [tuple(data[col] for col in columns) for data in data_list]
            else:
                # 使用 INSERT ... ON CONFLICT DO UPDATE（DuckDB/PG 风格 Upsert）
                columns, values, update_clause = DBService.to_upsert_params(data_list, unique_keys)
                
                if not columns:
                    return
                
                columns_sql = ', '.join(columns)
                conflict_cols = ', '.join(unique_keys)
            
            if not self.conn:
                raise RuntimeError("DatabaseManager not initialized.")
            
            # 批量插入（分批处理，避免 SQL 语句过长）
            INSERT_BATCH_SIZE = 5000
            for i in range(0, len(values), INSERT_BATCH_SIZE):
                batch_values = values[i:i+INSERT_BATCH_SIZE]
                
                # 构建批量插入 SQL
                values_list = []
                for val in batch_values:
                    formatted_values = []
                    for v in val:
                        if v is None:
                            formatted_values.append('NULL')
                        elif isinstance(v, str):
                            escaped = v.replace("'", "''")
                            formatted_values.append(f"'{escaped}'")
                        elif isinstance(v, (int, float)):
                            import math
                            if isinstance(v, float) and math.isnan(v):
                                formatted_values.append('NULL')
                            else:
                                formatted_values.append(str(v))
                        elif isinstance(v, bool):
                            formatted_values.append('TRUE' if v else 'FALSE')
                        elif isinstance(v, (datetime, date)):
                            if isinstance(v, datetime):
                                formatted_values.append(f"'{v.strftime('%Y-%m-%d %H:%M:%S')}'")
                            else:
                                formatted_values.append(f"'{v.strftime('%Y-%m-%d')}'")
                        else:
                            escaped_val = str(v).replace("'", "''")
                            formatted_values.append(f"'{escaped_val}'")
                    values_list.append(f"({', '.join(formatted_values)})")
                
                # 执行批量插入
                if not unique_keys:
                    # 纯 INSERT
                    batch_query = f"INSERT INTO {table_name} ({columns_sql}) VALUES {', '.join(values_list)}"
                else:
                    # INSERT ... ON CONFLICT
                    if update_clause:
                        batch_query = (
                            f"INSERT INTO {table_name} ({columns_sql}) VALUES {', '.join(values_list)} "
                            f"ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_clause}"
                        )
                    else:
                        batch_query = (
                            f"INSERT INTO {table_name} ({columns_sql}) VALUES {', '.join(values_list)} "
                            f"ON CONFLICT ({conflict_cols}) DO NOTHING"
                        )
                
                self.conn.execute(batch_query)
            
            if callback:
                callback(table_name, len(data_list))
                    
        except Exception as e:
            logger.error(f"Failed to write to {table_name}: {e}")
            raise
    
    def flush_writes(self, table_name: Optional[str] = None):
        """
        立即刷新指定表或所有表的待写入数据
        
        Args:
            table_name: 表名，None 表示刷新所有表
        """
        if self._write_queue:
            self._write_queue.flush(table_name)
    
    def get_write_stats(self) -> Dict[str, Any]:
        """获取写入统计信息"""
        if self._write_queue:
            return self._write_queue.get_stats()
        return {}
    
    def wait_for_writes(self, timeout: float = 30.0):
        """
        等待所有写入完成
        
        Args:
            timeout: 超时时间（秒）
        """
        if self._write_queue:
            self._write_queue.wait_for_writes(timeout)
    
    def close(self):
        """关闭数据库连接和写入队列"""
        # 关闭写入队列（会刷新所有待写入数据）
        if self._write_queue:
            self._write_queue.shutdown()
            self._write_queue = None
        
        # 关闭数据库连接
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
            self.conn = None
        
        self._initialized = False
    
    def __del__(self):
        """析构函数：确保连接和队列关闭"""
        try:
            self.close()
        except:
            pass
