"""
TableManager - 表操作 API

职责：
- 查询执行
- 批量写入队列管理
- 直接写入（兜底方案）
"""
from typing import List, Dict, Any, Optional, Callable
import logging

from core.infra.db.table_queriers.services.batch_operation_queue import BatchWriteQueue
from core.infra.db.helpers.db_helpers import DBHelper
from core.infra.db.table_queriers.adapters.base_adapter import BaseDatabaseAdapter


logger = logging.getLogger(__name__)


class TableManager:
    """
    表操作管理器
    
    职责：
    - 查询执行
    - 批量写入队列管理
    - 直接写入（兜底方案）
    """
    
    def __init__(
        self,
        adapter: BaseDatabaseAdapter,
        config: Dict,
        is_verbose: bool = False
    ):
        """
        初始化表管理器
        
        Args:
            adapter: 数据库适配器
            config: 数据库配置
            is_verbose: 是否输出详细日志
        """
        self.adapter = adapter
        self.config = config
        self.is_verbose = is_verbose
        
        # 批量写入队列（延迟初始化）
        self._write_queue: Optional[BatchWriteQueue] = None
    
    def initialize_write_queue(self):
        """
        初始化批量写入队列
        
        注意：如果队列已存在，不会重复初始化（避免重复启动线程）
        """
        # 如果队列已存在且正在运行，不重复初始化
        if self._write_queue is not None and self._write_queue._is_running:
            return
        
        try:
            # 从配置读取批量写入参数
            batch_config = self.config.get('batch_write', {})
            batch_size = batch_config.get('batch_size', 1000)
            flush_interval = batch_config.get('flush_interval', 5.0)
            enable = batch_config.get('enable', True)
            
            # 读取高级配置（insert_batch_size）
            advanced_config = batch_config.get('_advanced', {})
            insert_batch_size = advanced_config.get('insert_batch_size', 5000)
            
            # 创建 BatchWriteQueue（需要传入一个 table_manager 对象）
            self._write_queue = BatchWriteQueue(
                table_manager=self,
                batch_size=batch_size,
                flush_interval=flush_interval,
                enable=enable,
                insert_batch_size=insert_batch_size
            )
            
            if self.is_verbose and enable:
                logger.info(
                    f"✅ 批量写入队列已启用 "
                    f"(batch_size={batch_size}, flush_interval={flush_interval}s, "
                    f"insert_batch_size={insert_batch_size})"
                )
            elif not enable and self.is_verbose:
                logger.info("ℹ️  批量写入队列已禁用（直接写入模式）")
        except Exception as e:
            logger.warning(f"⚠️ 初始化批量写入队列失败: {e}，将使用直接写入模式")
            self._write_queue = None
    
    def execute_sync_query(self, query: str, params: Any = None) -> List[Dict[str, Any]]:
        """
        执行同步查询语句
        
        Args:
            query: SQL 查询语句（使用 %s 占位符，适配器会自动转换）
            params: 查询参数
            
        Returns:
            查询结果列表（字典格式）
        """
        if not self.adapter:
            raise RuntimeError("TableManager not initialized. Adapter is required.")
        
        # 使用适配器的 execute_query 方法（会自动处理占位符转换）
        return self.adapter.execute_query(query, params)
    
    def queue_write(
        self,
        table_name: str,
        data_list: List[Dict],
        unique_keys: List[str],
        callback: Callable = None
    ):
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
        
        # 延迟初始化：只在第一次需要写入时才初始化批量写入队列
        if self._write_queue is None:
            self.initialize_write_queue()
        
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
            if not data_list:
                return
            
            if not unique_keys:
                # 纯 INSERT（不需要去重）
                columns, placeholders = DBHelper.to_columns_and_values(data_list)
                columns_sql = ', '.join(columns)
                values = [tuple(data[col] for col in columns) for data in data_list]
            else:
                # 使用 INSERT ... ON CONFLICT DO UPDATE（PostgreSQL/SQLite 风格 Upsert）
                columns, values, update_clause = DBHelper.to_upsert_params(data_list, unique_keys)
                
                if not columns:
                    return
                
                columns_sql = ', '.join(columns)
                conflict_cols = ', '.join(unique_keys)
            
            if not self.adapter:
                raise RuntimeError("TableManager not initialized. Adapter is required.")
            
            # 使用适配器的 execute_batch 方法进行批量插入
            # 构建 INSERT SQL
            placeholder = self.adapter.get_placeholder()
            placeholders = ', '.join([placeholder] * len(columns))
            
            if not unique_keys:
                # 纯 INSERT
                insert_sql = f"INSERT INTO {table_name} ({columns_sql}) VALUES ({placeholders})"
                # 使用 execute_batch
                self.adapter.execute_batch(insert_sql, values)
            else:
                # INSERT ... ON CONFLICT
                if update_clause:
                    insert_sql = (
                        f"INSERT INTO {table_name} ({columns_sql}) VALUES ({placeholders}) "
                        f"ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_clause}"
                    )
                else:
                    insert_sql = (
                        f"INSERT INTO {table_name} ({columns_sql}) VALUES ({placeholders}) "
                        f"ON CONFLICT ({conflict_cols}) DO NOTHING"
                    )
                # 使用 execute_batch
                self.adapter.execute_batch(insert_sql, values)
            
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
        """关闭写入队列"""
        # 关闭写入队列（会刷新所有待写入数据）
        if self._write_queue:
            self._write_queue.shutdown()
            self._write_queue = None
