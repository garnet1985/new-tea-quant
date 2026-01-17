"""
SQLiteAdapter - SQLite 数据库适配器

实现 SQLite 数据库的连接和操作。
"""
import sqlite3
from typing import Dict, List, Any, Optional
from contextlib import contextmanager
from pathlib import Path
from loguru import logger

from .base_adapter import BaseDatabaseAdapter


class SQLiteAdapter(BaseDatabaseAdapter):
    """
    SQLite 数据库适配器
    
    特性：
    - 单文件数据库
    - 无需连接池
    - 支持只读模式（多进程并发读）
    """
    
    def __init__(self, config: Dict[str, Any], is_verbose: bool = False, read_only: bool = False):
        """
        初始化 SQLite 适配器
        
        Args:
            config: SQLite 配置字典
                - db_path: 数据库文件路径
                - timeout: 超时时间（默认 5.0 秒）
            is_verbose: 是否输出详细日志
            read_only: 是否以只读模式打开
        """
        self.config = config
        self.is_verbose = is_verbose
        self.read_only = read_only
        self.conn: Optional[sqlite3.Connection] = None
        self._initialized = False
    
    def connect(self, config: Dict[str, Any] = None) -> sqlite3.Connection:
        """
        建立 SQLite 连接
        
        Args:
            config: 数据库配置（如果提供，会覆盖初始化时的配置）
            
        Returns:
            SQLite 连接对象
        """
        if config:
            self.config = config
        
        try:
            db_path = Path(self.config['db_path'])
            
            # 确保数据库文件目录存在
            if not self.read_only:
                db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 连接 SQLite
            if self.read_only:
                # 只读模式：URI 方式打开
                uri = f"file:{db_path}?mode=ro"
                self.conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
                if self.is_verbose:
                    logger.info(f"📖 以只读模式连接 SQLite: {db_path}")
            else:
                self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
            
            # 设置行工厂，返回字典格式
            self.conn.row_factory = sqlite3.Row
            
            # 设置超时
            timeout = self.config.get('timeout', 5.0)
            self.conn.execute(f"PRAGMA busy_timeout = {int(timeout * 1000)}")
            
            self._initialized = True
            
            if self.is_verbose:
                logger.info(f"✅ SQLite 连接成功: {db_path}")
                logger.info(f"   超时时间: {timeout}s")
            
            return self.conn
            
        except Exception as e:
            logger.error(f"❌ SQLite 连接失败: {e}")
            raise
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self._initialized = False
            if self.is_verbose:
                logger.info("✅ SQLite 连接已关闭")
    
    def execute_query(self, query: str, params: Any = None) -> List[Dict[str, Any]]:
        """
        执行查询语句
        
        Args:
            query: SQL 查询语句（使用 ? 占位符，会自动转换 %s -> ?）
            params: 查询参数
            
        Returns:
            查询结果列表（字典格式）
        """
        if not self.conn:
            raise RuntimeError("SQLite 适配器未初始化，请先调用 connect()")
        
        try:
            # 统一转换占位符：%s -> ?
            query = query.replace("%s", "?")
            
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            cursor.close()
            
            if not results:
                return []
            
            # sqlite3.Row 转换为字典
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"执行查询失败: {e}\n查询: {query}\n参数: {params}")
            raise
    
    def execute_write(self, query: str, params: Any = None) -> int:
        """
        执行写入语句
        
        Args:
            query: SQL 写入语句
            params: 查询参数
            
        Returns:
            影响的行数
        """
        if not self.conn:
            raise RuntimeError("SQLite 适配器未初始化，请先调用 connect()")
        
        if self.read_only:
            raise RuntimeError("SQLite 连接为只读模式，无法执行写入操作")
        
        try:
            # 统一转换占位符：%s -> ?
            query = query.replace("%s", "?")
            
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            self.conn.commit()
            rowcount = cursor.rowcount
            cursor.close()
            
            return rowcount
            
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            logger.error(f"执行写入失败: {e}\n查询: {query}\n参数: {params}")
            raise
    
    def execute_batch(self, query: str, params_list: List[Any]) -> int:
        """
        批量执行写入语句
        
        Args:
            query: SQL 写入语句
            params_list: 参数列表
            
        Returns:
            总影响的行数
        """
        if not self.conn:
            raise RuntimeError("SQLite 适配器未初始化，请先调用 connect()")
        
        if self.read_only:
            raise RuntimeError("SQLite 连接为只读模式，无法执行写入操作")
        
        try:
            # 统一转换占位符：%s -> ?
            query = query.replace("%s", "?")
            
            cursor = self.conn.cursor()
            cursor.executemany(query, params_list)
            self.conn.commit()
            rowcount = cursor.rowcount
            cursor.close()
            
            return rowcount
            
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            logger.error(f"批量写入失败: {e}\n查询: {query}\n记录数: {len(params_list)}")
            raise
    
    @contextmanager
    def transaction(self):
        """
        事务上下文管理器
        
        使用方式:
            with adapter.transaction() as cursor:
                cursor.execute("INSERT ...")
                cursor.execute("UPDATE ...")
                # 自动提交或回滚
        """
        if not self.conn:
            raise RuntimeError("SQLite 适配器未初始化，请先调用 connect()")
        
        cursor = self.conn.cursor()
        try:
            yield cursor
            self.conn.commit()
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            cursor.close()
    
    def get_placeholder(self) -> str:
        """返回 SQLite 占位符类型"""
        return '?'
    
    def get_connection(self):
        """
        获取数据库连接（用于需要直接访问连接的场景）
        
        Returns:
            SQLite 连接对象
        """
        if not self.conn:
            raise RuntimeError("SQLite 适配器未初始化，请先调用 connect()")
        return self.conn
    
    def is_table_exists(self, table_name: str) -> bool:
        """
        检查表是否存在
        
        Args:
            table_name: 表名
            
        Returns:
            是否存在
        """
        query = """
            SELECT COUNT(*) as count 
            FROM sqlite_master 
            WHERE type='table' AND name = ?
        """
        try:
            result = self.execute_query(query, (table_name,))
            return result[0]['count'] > 0 if result else False
        except Exception as e:
            logger.error(f"检查表是否存在失败: {e}")
            return False
