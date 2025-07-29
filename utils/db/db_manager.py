"""
统一的MySQL数据库管理器
支持同步和异步操作，默认线程安全
"""
import pymysql
import threading
import time
import queue
import asyncio
from typing import Optional, Dict, List, Any, Callable
from contextlib import contextmanager
from loguru import logger

from .db_config import DB_CONFIG


class DatabaseManager:
    """统一的MySQL数据库管理器 - 支持同步和异步操作，默认线程安全"""
    
    def __init__(self, is_verbose: bool = False, enable_thread_safety: bool = True):
        # 原有属性（保持兼容性）
        self.sync_connection = None
        self.is_sync_connected = False
        
        # 异步连接
        self.async_pool = None
        self.is_async_initialized = False

        # 线程安全属性
        self.enable_thread_safety = enable_thread_safety
        self._local = threading.local() if enable_thread_safety else None
        self._connection_pool = queue.Queue(maxsize=10) if enable_thread_safety else None
        self._write_queue = queue.Queue() if enable_thread_safety else None
        self._write_thread = None
        self._write_thread_running = False
        
        # 表缓存 - 简化为单一字典
        self.tables = {}
        
        # 注册的自定义表
        self.registered_tables = {}
        
        # 表缓存锁（用于保护表实例缓存）
        self._tables_lock = threading.Lock() if enable_thread_safety else None
        
        # 统计信息
        self._stats = {
            'connections_created': 0,
            'connections_reused': 0,
            'writes_queued': 0,
            'writes_completed': 0,
            'writes_failed': 0,
            'batch_writes': 0
        }
        self._stats_lock = threading.Lock()

        # 全局回调系统
        self._global_callbacks = []
        self._callbacks_lock = threading.Lock()

        self.is_verbose = is_verbose
        
        # 启动写入线程（如果启用线程安全）
        if enable_thread_safety:
            self._start_write_thread()

        self.initialize()
    
    # ==================== 线程安全相关方法 ====================

    def set_verbose(self, is_verbose: bool):
        self.is_verbose = is_verbose
    
    def _start_write_thread(self):
        """启动写入线程"""
        if self._write_thread is None or not self._write_thread.is_alive():
            self._write_thread_running = True
            self._write_thread = threading.Thread(target=self._write_worker, daemon=True)
            self._write_thread.start()
            if self.is_verbose:
                logger.info("Database write thread started")
    
    def _stop_write_thread(self):
        """停止写入线程"""
        self._write_thread_running = False
        if self._write_thread and self._write_thread.is_alive():
            self._write_thread.join(timeout=5)
            if self.is_verbose:
                logger.info("Database write thread stopped")
    
    def _create_connection(self) -> pymysql.Connection:
        """创建新的数据库连接"""
        try:
            connection = pymysql.connect(
                host=DB_CONFIG['base']['host'],
                user=DB_CONFIG['base']['user'],
                password=DB_CONFIG['base']['password'],
                database=DB_CONFIG['base']['database'],
                port=DB_CONFIG['base']['port'],
                charset=DB_CONFIG['base']['charset'],
                autocommit=DB_CONFIG['base']['autocommit'],
                max_allowed_packet=DB_CONFIG['performance']['max_allowed_packet'],
                connect_timeout=DB_CONFIG['timeout']['connection'],
                read_timeout=DB_CONFIG['timeout']['read'],
                write_timeout=DB_CONFIG['timeout']['write'],
            )
            
            with self._stats_lock:
                self._stats['connections_created'] += 1
            
            if self.is_verbose:
                logger.debug(f"Created new database connection (total: {self._stats['connections_created']})")
            return connection
            
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            raise
    
    def _get_thread_safe_connection(self) -> pymysql.Connection:
        """获取线程安全的数据库连接"""
        # 检查线程本地连接
        if hasattr(self._local, 'connection'):
            try:
                self._local.connection.ping(reconnect=True)
                return self._local.connection
            except Exception as e:
                logger.warning(f"Thread local connection invalid, creating new one: {e}")
                try:
                    self._local.connection.close()
                except:
                    pass
        
        # 尝试从连接池获取
        try:
            connection = self._connection_pool.get_nowait()
            with self._stats_lock:
                self._stats['connections_reused'] += 1
            if self.is_verbose:
                logger.debug("Reused connection from pool")
        except queue.Empty:
            # 池中没有可用连接，创建新的
            connection = self._create_connection()
        
        # 存储到线程本地
        self._local.connection = connection
        return connection
    
    # ==================== 同步连接方法 ====================

    def initialize(self):
        """初始化数据库管理器（包含连接、创建数据库、初始化策略模型、创建表）"""
        try:
            # 连接数据库
            self.connect_sync()
            
            # 创建数据库（如果不存在）
            self.create_db()
            
            # 初始化策略模型（这会注册表到数据库管理器）
            self._initialize_strategy_models()
            
            # 创建所有表（包括注册的策略表）
            self.create_tables()
            
            if self.is_verbose:
                logger.info("Database manager fully initialized")
                
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def _initialize_strategy_models(self):
        """初始化策略模型和策略管理器"""
        try:
            from app.analyser.strategy.strategy_manager import StrategyManager
            
            # 创建策略管理器
            self.strategy_manager = StrategyManager(self)
            
            # 初始化策略（这会注册表到数据库管理器）
            self.strategy_manager.initialize_strategies()
            
            if self.is_verbose:
                logger.info("Strategy models and manager initialized")
                
        except Exception as e:
            logger.error(f"Strategy models initialization failed: {e}")
            raise
    
    def connect_sync(self):
        """建立同步数据库连接"""
        try:
            self.sync_connection = pymysql.connect(
                host=DB_CONFIG['base']['host'],
                user=DB_CONFIG['base']['user'],
                password=DB_CONFIG['base']['password'],
                database=DB_CONFIG['base']['database'],
                port=DB_CONFIG['base']['port'],
                charset=DB_CONFIG['base']['charset'],
                autocommit=DB_CONFIG['base']['autocommit'],
                max_allowed_packet=DB_CONFIG['performance']['max_allowed_packet'],
                connect_timeout=DB_CONFIG['timeout']['connection'],
                read_timeout=DB_CONFIG['timeout']['read'],
                write_timeout=DB_CONFIG['timeout']['write'],
            )
            self.is_sync_connected = True
            if self.is_verbose:
                logger.info("Synchronous database connected successfully")
        except pymysql.err.OperationalError as e:
            # 检查是否是数据库不存在的错误
            if e.args[0] == 1049:  # Unknown database
                logger.warning(f"Database '{DB_CONFIG['base']['database']}' does not exist, creating it...")
                if self.create_db():
                    # 重新尝试连接
                    self.sync_connection = pymysql.connect(
                        host=DB_CONFIG['base']['host'],
                        user=DB_CONFIG['base']['user'],
                        password=DB_CONFIG['base']['password'],
                        database=DB_CONFIG['base']['database'],
                        port=DB_CONFIG['base']['port'],
                        charset=DB_CONFIG['base']['charset'],
                        autocommit=DB_CONFIG['base']['autocommit'],
                        max_allowed_packet=DB_CONFIG['performance']['max_allowed_packet'],
                        connect_timeout=DB_CONFIG['timeout']['connection'],
                        read_timeout=DB_CONFIG['timeout']['read'],
                        write_timeout=DB_CONFIG['timeout']['write'],
                    )
                    self.is_sync_connected = True
                    if self.is_verbose:
                        logger.info("Synchronous database connected successfully after creation")
                else:
                    logger.error("Failed to create database")
                    raise
            else:
                logger.error(f"Failed to connect to database synchronously: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to connect to database synchronously: {e}")
            raise
    
    def disconnect_sync(self):
        """断开同步数据库连接"""
        if self.sync_connection:
            self.sync_connection.close()
            self.is_sync_connected = False
            if self.is_verbose:
                logger.info("Synchronous database disconnected")

    def create_db(self):
        """创建数据库（如果不存在）"""
        try:
            # 连接到MySQL服务器（不指定数据库）
            temp_connection = pymysql.connect(
                host=DB_CONFIG['base']['host'],
                user=DB_CONFIG['base']['user'],
                password=DB_CONFIG['base']['password'],
                port=DB_CONFIG['base']['port'],
                charset=DB_CONFIG['base']['charset'],
            )
            
            with temp_connection.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['base']['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci")
                logger.info(f"Database '{DB_CONFIG['base']['database']}' is ready")
            
            temp_connection.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            return False 

    def register_table(self, table_name, prefix, schema, model_class=None):
        """
        注册自定义表
        
        Args:
            table_name: 表名 (会自动添加 strategy 的 prefix)
            prefix: 表前缀
            schema: 表结构定义（字典格式）
            model_class: 自定义模型类 (可选, 继承自BaseTableModel)
        """
        # 确保表名有前缀
        if not prefix:
            logger.error(f"prefix is required for table: {table_name}")
        else:   
            table_name = prefix + '_' + table_name
        
        # 存储表信息
        self.registered_tables[table_name] = {
            'schema': schema,
            'model_class': model_class
        }
        
        if self.is_verbose:
            logger.info(f"{table_name} table is registered")
        return table_name

    
    def create_tables(self):
        """创建所有表（基础表和注册表）"""
        try:
            # 创建基础表
            self._create_base_tables()
            
            # 创建注册的自定义表
            self._create_registered_tables()
            
            if self.is_verbose:
                logger.info("All tables created")
        except Exception as e:
            logger.error(f"创建表失败: {e}")
            raise
    
    def _create_base_tables(self):
        """创建基础表"""
        import os
        
        # 获取 tables 目录下的所有表
        tables_dir = os.path.join(os.path.dirname(__file__), 'tables')
        if os.path.exists(tables_dir):
            for table_name in os.listdir(tables_dir):
                table_path = os.path.join(tables_dir, table_name)
                if os.path.isdir(table_path):
                    # 检查是否有 schema.json
                    schema_file = os.path.join(table_path, 'schema.json')
                    if os.path.exists(schema_file):
                        table_model = self._get_table_model(table_name)
                        table_model.create_table()
                        self.tables[table_name] = table_model
                        if self.is_verbose:
                            logger.info(f"created base table: {table_name}")
    
    def _create_registered_tables(self):
        """创建注册的自定义表"""
        for table_name, table_info in self.registered_tables.items():
            try:
                # 创建自定义表模型
                if table_info['model_class']:
                    # 使用自定义模型类 - 只传递数据库连接
                    table_model = table_info['model_class'](self)
                else:
                    # 使用基础模型类
                    from .db_model import BaseTableModel
                    table_model = BaseTableModel(table_name, self)
                
                # 设置schema（如果不是自定义模型类）
                if not table_info['model_class']:
                    table_model.schema = table_info['schema']
                
                # 创建表（使用自定义表名）
                custom_table_name = None
                if hasattr(table_model, 'table_full_name'):
                    custom_table_name = table_model.table_full_name
                table_model.create_table(custom_table_name)
                self.tables[table_name] = table_model
                
                if self.is_verbose:
                    logger.info(f"created registered table: {table_name}")
                
            except Exception as e:
                logger.error(f"创建注册表 {table_name} 失败: {e}")
                raise
    
    def get_table_instance(self, table_name: str):
        """获取表实例（线程安全）"""
        # 如果启用线程安全，使用锁保护表缓存
        if self.enable_thread_safety and self._tables_lock:
            with self._tables_lock:
                return self._get_table_instance_internal(table_name)
        else:
            return self._get_table_instance_internal(table_name)
    
    def _get_table_instance_internal(self, table_name: str):
        """获取表实例的内部实现"""
        # 首先检查缓存
        if table_name in self.tables:
            return self.tables[table_name]
        
        # 检查是否是注册表
        if table_name in self.registered_tables:
            table_info = self.registered_tables[table_name]
            if table_info['model_class']:
                table_model = table_info['model_class'](table_name, self)
            else:
                from .db_model import BaseTableModel
                table_model = BaseTableModel(table_name, self)
            
            table_model.schema = table_info['schema']
            self.tables[table_name] = table_model
            return table_model
        
        # 尝试获取基础表
        table_model = self._get_table_model(table_name)
        self.tables[table_name] = table_model
        return table_model
    
    def _get_table_model(self, table_name: str):
        """根据表名获取对应的模型实例"""
        import os
        import importlib.util
        
        # 构建表目录路径
        table_dir = os.path.join(os.path.dirname(__file__), 'tables', table_name)
        model_file = os.path.join(table_dir, 'model.py')
        
        # 检查是否存在自定义模型文件
        if os.path.exists(model_file):
            try:
                # 动态导入自定义模型
                spec = importlib.util.spec_from_file_location(f"{table_name}_model", model_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 查找模型类（假设类名为 TableNameModel 或 Model）
                model_class = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        hasattr(attr, '__bases__') and 
                        any('BaseTableModel' in str(base) for base in attr.__bases__)):
                        model_class = attr
                        break
                
                if model_class:
                    if self.is_verbose:
                        logger.info(f"Using custom model for table: {table_name}")
                    return model_class(table_name, self)
                else:
                    logger.warning(f"Custom model file found but no valid model class in {model_file}")
                    
            except Exception as e:
                logger.error(f"Failed to load custom model for {table_name}: {e}")
        
        # 如果没有自定义模型或加载失败，使用 BaseTableModel
        from .db_model import BaseTableModel
        if self.is_verbose:
            logger.info(f"Using BaseTableModel for table: {table_name}")
        return BaseTableModel(table_name, self)

    def _generate_create_table_sql(self, schema_data: dict) -> str:
        """根据schema数据生成CREATE TABLE SQL语句"""
        table_name = schema_data['name']
        primary_key = schema_data.get('primaryKey', 'id')
        fields = schema_data['fields']
        
        # 构建字段定义
        field_definitions = []
        for field in fields:
            field_name = field['name']
            field_type = field['type'].upper()
            is_required = field.get('isRequired', False)
            
            # 处理字段类型和长度
            if field_type == 'VARCHAR' and 'length' in field:
                field_def = f"`{field_name}` {field_type}({field['length']})"
            elif field_type == 'TEXT':
                field_def = f"`{field_name}` {field_type}"
            elif field_type == 'TINYINT':
                field_def = f"`{field_name}` {field_type}(1)"
            elif field_type == 'DATETIME':
                field_def = f"`{field_name}` {field_type}"
            else:
                field_def = f"`{field_name}` {field_type}"
            
            # 添加约束
            if is_required:
                field_def += " NOT NULL"
            else:
                field_def += " NULL"
            
            field_definitions.append(field_def)
        
        # 添加主键约束
        if primary_key and primary_key != 'id':
            field_definitions.append(f"PRIMARY KEY (`{primary_key}`)")
        
        # 生成完整的CREATE TABLE语句
        field_definitions_str = ',\n            '.join(field_definitions)
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS `{table_name}` (
            {field_definitions_str}
        ) ENGINE=InnoDB DEFAULT CHARSET={DB_CONFIG['base']['charset']} COLLATE={DB_CONFIG['base']['charset']}_general_ci;
        """
        
        return create_sql
    
    @contextmanager
    def get_sync_cursor(self):
        """获取同步数据库游标的上下文管理器（支持线程安全）"""
        if self.enable_thread_safety:
            # 线程安全模式
            connection = self._get_thread_safe_connection()
            cursor = None
            
            try:
                cursor = connection.cursor(pymysql.cursors.DictCursor)
                yield cursor
            except Exception as e:
                logger.error(f"Database cursor error: {e}")
                try:
                    connection.rollback()
                except:
                    pass
                raise
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass
        else:
            # 原有模式
            if not self.is_sync_connected or self.sync_connection is None:
                self.connect_sync()
            
            # 检查连接是否有效
            try:
                self.sync_connection.ping(reconnect=True)
            except Exception as e:
                logger.warning(f"Database connection lost, reconnecting: {e}")
                self.connect_sync()
            
            cursor = None
            try:
                cursor = self.sync_connection.cursor(pymysql.cursors.DictCursor)
                yield cursor
            except Exception as e:
                logger.error(f"Synchronous database cursor error: {e}")
                if self.sync_connection:
                    try:
                        self.sync_connection.rollback()
                    except:
                        pass
                # 如果是连接相关错误，尝试重连
                if "Packet sequence number wrong" in str(e) or "settimeout" in str(e):
                    logger.warning("Connection error detected, will reconnect on next use")
                    self.is_sync_connected = False
                    self.sync_connection = None
                raise
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass
    
    def execute_sync_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """执行同步查询语句（支持线程安全）"""
        with self.get_sync_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_sync_update(self, query: str, params: Optional[tuple] = None) -> int:
        """执行同步更新语句（支持线程安全）"""
        with self.get_sync_cursor() as cursor:
            affected_rows = cursor.execute(query, params)
            cursor.connection.commit()
            return affected_rows
    
    def execute_many(self, query: str, params_list: List[tuple], batch_size: int = 1000) -> int:
        """批量执行SQL语句（线程安全）"""
        if not params_list:
            return 0
        
        total_affected = 0
        
        # 分批处理
        for i in range(0, len(params_list), batch_size):
            batch = params_list[i:i + batch_size]
            
            with self.get_sync_cursor() as cursor:
                affected_rows = cursor.executemany(query, batch)
                cursor.connection.commit()
                total_affected += affected_rows
                
                if self.is_verbose:
                    logger.debug(f"Batch write completed: {len(batch)} records, affected: {affected_rows}")
        
        with self._stats_lock:
            self._stats['batch_writes'] += 1
        
        return total_affected
    
    def queue_write(self, table_name: str, data_list: List[Dict[str, Any]], 
                   unique_keys: List[str], callback: Optional[Callable] = None):
        """将写入任务加入队列（异步写入）"""
        if not self.enable_thread_safety:
            logger.warning("Thread safety not enabled, falling back to sync write")
            return self._execute_batch_write(table_name, data_list, unique_keys)
        
        write_task = {
            'table_name': table_name,
            'data_list': data_list,
            'unique_keys': unique_keys,
            'callback': callback,
            'timestamp': time.time()
        }
        
        self._write_queue.put(write_task)
        
        with self._stats_lock:
            self._stats['writes_queued'] += 1
        
        if self.is_verbose:
            logger.info(f"Write task queued for table {table_name}: {len(data_list)} records")
    
    def _write_worker(self):
        """写入工作线程"""
        if self.is_verbose:
            logger.info("Database write worker started")
        
        while self._write_thread_running:
            try:
                # 获取写入任务
                try:
                    write_task = self._write_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # 执行写入
                try:
                    result = self._execute_batch_write(
                        write_task['table_name'],
                        write_task['data_list'],
                        write_task['unique_keys']
                    )
                    
                    # 调用回调函数
                    if write_task['callback']:
                        try:
                            write_task['callback'](result)
                        except Exception as e:
                            logger.error(f"Write callback error: {e}")
                    
                    with self._stats_lock:
                        self._stats['writes_completed'] += 1
                    
                    if self.is_verbose:
                        logger.debug(f"Write task completed for {write_task['table_name']}: {result} records")
                    
                except Exception as e:
                    logger.error(f"Write task failed for {write_task['table_name']}: {e}")
                    with self._stats_lock:
                        self._stats['writes_failed'] += 1
                
                finally:
                    self._write_queue.task_done()
                    
            except Exception as e:
                logger.error(f"Write worker error: {e}")
                time.sleep(0.1)
        
        logger.info("Database write worker stopped")
    
    def _execute_batch_write(self, table_name: str, data_list: List[Dict[str, Any]], 
                           unique_keys: List[str]) -> int:
        """执行批量写入"""
        if not data_list:
            return 0
        
        # 构建SQL语句
        update_clause = ', '.join([f"{k} = VALUES({k})" for k in data_list[0].keys() if k not in unique_keys])
        columns = list(data_list[0].keys())
        placeholders = ', '.join(['%s'] * len(columns))
        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_clause}"
        
        # 准备数据
        values = [tuple(data[col] for col in columns) for data in data_list]
        
        # 分批执行
        return self.execute_many(query, values)
    
    def add_global_callback(self, callback: Callable):
        """添加全局回调函数，在所有异步写入完成后执行"""
        with self._callbacks_lock:
            self._global_callbacks.append(callback)
    
    def remove_global_callback(self, callback: Callable):
        """移除全局回调函数"""
        with self._callbacks_lock:
            if callback in self._global_callbacks:
                self._global_callbacks.remove(callback)
    
    def clear_global_callbacks(self):
        """清除所有全局回调函数"""
        with self._callbacks_lock:
            self._global_callbacks.clear()
    
    async def wait_for_writes(self, timeout: Optional[float] = None):
        """等待所有写入任务完成，并执行全局回调"""
        if not self.enable_thread_safety:
            return
        
        try:
            # 使用 asyncio.to_thread 在线程池中运行同步的 join 操作
            await asyncio.to_thread(self._write_queue.join)
            logger.info("All write tasks completed")
            
            # 执行全局回调
            with self._callbacks_lock:
                callbacks_to_execute = self._global_callbacks.copy()
            
            for callback in callbacks_to_execute:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Global callback error: {e}")
                    
        except Exception as e:
            logger.error(f"Error waiting for writes: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._stats_lock:
            stats = self._stats.copy()
        
        if self.enable_thread_safety:
            stats['queue_size'] = self._write_queue.qsize()
            stats['pool_size'] = self._connection_pool.qsize()
        
        return stats
    
    def close(self):
        """关闭数据库管理器"""
        logger.info("Closing DatabaseManager...")
        
        # 停止写入线程
        if self.enable_thread_safety:
            self._stop_write_thread()
            
            # 等待写入完成
            self.wait_for_writes(timeout=10)
            
            # 关闭所有连接
            while not self._connection_pool.empty():
                try:
                    connection = self._connection_pool.get_nowait()
                    connection.close()
                except:
                    pass
            
            # 关闭线程本地连接
            if hasattr(self._local, 'connection'):
                try:
                    self._local.connection.close()
                except:
                    pass
        
        # 关闭原有连接
        if self.sync_connection:
            try:
                self.sync_connection.close()
            except:
                pass
        
        logger.info("DatabaseManager closed")
    
    # ==================== 兼容性方法 ====================
    
    def connect(self):
        """兼容性方法：建立同步连接"""
        return self.connect_sync()
    
    def disconnect(self):
        """兼容性方法：断开同步连接"""
        return self.disconnect_sync()
    
    @contextmanager
    def get_cursor(self):
        """兼容性方法：获取同步游标"""
        return self.get_sync_cursor()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """兼容性方法：执行同步查询"""
        return self.execute_sync_query(query, params)
    
    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """兼容性方法：执行同步更新"""
        return self.execute_sync_update(query, params)
    

# 全局数据库管理器实例（默认启用线程安全）
db_manager = DatabaseManager(enable_thread_safety=True)


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例（默认线程安全）"""
    return db_manager


def get_sync_db_manager() -> DatabaseManager:
    """获取同步数据库管理器实例（兼容性函数）"""
    return db_manager


def close_db_manager():
    """关闭数据库管理器"""
    global db_manager
    if db_manager:
        db_manager.close()
        db_manager = None 