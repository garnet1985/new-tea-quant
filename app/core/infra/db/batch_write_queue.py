"""
批量写入队列 - 解决 DuckDB 并发写入问题

功能：
- 收集多线程的写入请求
- 达到阈值后批量写入
- 单线程执行写入，避免锁冲突
- 支持超时刷新和强制刷新
"""
import threading
import time
from typing import Dict, List, Any, Optional, Callable
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, date
from loguru import logger


@dataclass
class WriteRequest:
    """写入请求"""
    table_name: str
    data_list: List[Dict[str, Any]]
    unique_keys: List[str]
    callback: Optional[Callable] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class BatchWriteQueue:
    """
    批量写入队列
    
    解决 DuckDB 单连接写入的并发问题：
    - 多线程的写入请求先进入队列
    - 达到阈值（batch_size）或超时（flush_interval）后批量写入
    - 单线程执行写入，避免锁冲突
    """
    
    def __init__(
        self,
        db_manager,
        batch_size: int = 1000,
        flush_interval: float = 5.0,
        enable: bool = True
    ):
        """
        初始化批量写入队列
        
        Args:
            db_manager: DatabaseManager 实例
            batch_size: 批量写入阈值（达到此数量后立即写入）
            flush_interval: 刷新间隔（秒，超过此时间自动刷新）
            enable: 是否启用批量写入（False 时直接写入，用于调试）
        """
        self.db_manager = db_manager
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.enable = enable
        
        # 按表名分组的待写入数据
        self._queues: Dict[str, List[WriteRequest]] = defaultdict(list)
        self._lock = threading.Lock()
        
        # 写入线程控制
        self._write_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._flush_event = threading.Event()
        self._is_running = False
        
        # 统计信息
        self._stats = {
            'total_requests': 0,
            'total_writes': 0,
            'total_rows': 0,
            'errors': 0
        }
        
        if self.enable:
            self._start_write_thread()
    
    def _start_write_thread(self):
        """启动写入线程"""
        if self._is_running:
            return
        
        self._is_running = True
        self._stop_event.clear()
        self._write_thread = threading.Thread(
            target=self._write_worker,
            name="BatchWriteQueue-Writer",
            daemon=True
        )
        self._write_thread.start()
        logger.debug("批量写入队列线程已启动")
    
    def _write_worker(self):
        """写入工作线程（单线程执行所有写入）"""
        while not self._stop_event.is_set():
            try:
                # 等待刷新事件或超时
                event_set = self._flush_event.wait(timeout=self.flush_interval)
                if event_set:
                    self._flush_event.clear()
                
                # 检查是否有数据需要写入
                self._flush_all_if_needed()
                
            except Exception as e:
                logger.error(f"批量写入队列工作线程错误: {e}")
                import traceback
                logger.error(traceback.format_exc())
    
    def enqueue(
        self,
        table_name: str,
        data_list: List[Dict[str, Any]],
        unique_keys: List[str],
        callback: Optional[Callable] = None
    ):
        """
        将数据加入队列（非阻塞）
        
        Args:
            table_name: 表名
            data_list: 数据列表
            unique_keys: 唯一键列表
            callback: 回调函数（写入完成后调用）
        """
        if not self.enable:
            # 如果未启用，直接写入（用于调试或单线程场景）
            self._direct_write(table_name, data_list, unique_keys, callback)
            return
        
        if not data_list:
            return
        
        request = WriteRequest(
            table_name=table_name,
            data_list=data_list,
            unique_keys=unique_keys,
            callback=callback
        )
        
        with self._lock:
            self._queues[table_name].append(request)
            self._stats['total_requests'] += 1
            self._stats['total_rows'] += len(data_list)
            
            # 检查是否达到批量写入阈值
            total_pending = sum(len(req.data_list) for req in self._queues[table_name])
            if total_pending >= self.batch_size:
                # 触发立即刷新
                self._flush_event.set()
    
    def _flush_all_if_needed(self):
        """检查并刷新所有表的数据（如果达到条件）"""
        with self._lock:
            tables_to_flush = []
            
            for table_name, requests in self._queues.items():
                if not requests:
                    continue
                
                # 检查是否达到批量大小
                total_rows = sum(len(req.data_list) for req in requests)
                if total_rows >= self.batch_size:
                    tables_to_flush.append(table_name)
                    continue
                
                # 检查是否超时（最老的请求超过 flush_interval）
                oldest_request = min(requests, key=lambda r: r.timestamp)
                if time.time() - oldest_request.timestamp >= self.flush_interval:
                    tables_to_flush.append(table_name)
            
            # 刷新需要刷新的表
            for table_name in tables_to_flush:
                self._flush_table(table_name)
    
    def _flush_table(self, table_name: str):
        """刷新指定表的数据（必须在锁内调用）"""
        if table_name not in self._queues:
            return
        
        requests = self._queues[table_name]
        if not requests:
            return
        
        # 合并所有请求的数据
        all_data = []
        all_callbacks = []
        unique_keys = None
        
        for req in requests:
            all_data.extend(req.data_list)
            if req.callback:
                all_callbacks.append(req.callback)
            # 获取 unique_keys（假设同一表的所有请求使用相同的 unique_keys）
            if unique_keys is None:
                unique_keys = req.unique_keys
        
        # 清空队列
        del self._queues[table_name]
        
        # 释放锁后执行写入
        if all_data and unique_keys:
            # 在锁外执行写入
            try:
                self._direct_write(table_name, all_data, unique_keys, None)
                self._stats['total_writes'] += 1
                
                # 执行回调
                for callback in all_callbacks:
                    try:
                        callback(table_name, len(all_data))
                    except Exception as e:
                        logger.warning(f"写入回调执行失败: {e}")
                        
            except Exception as e:
                self._stats['errors'] += 1
                logger.error(f"批量写入失败 (表: {table_name}): {e}")
                import traceback
                logger.error(traceback.format_exc())
    
    def _direct_write(
        self,
        table_name: str,
        data_list: List[Dict[str, Any]],
        unique_keys: List[str],
        callback: Optional[Callable] = None
    ):
        """
        直接写入（不使用队列）
        
        注意：此方法不是线程安全的，应该在单线程环境中调用
        
        Args:
            table_name: 表名
            data_list: 数据列表
            unique_keys: 唯一键列表（如果为空，使用纯 INSERT；否则使用 INSERT ... ON CONFLICT）
            callback: 回调函数
        """
        if not data_list:
            return
        
        try:
            from .db_base_model import DBService
            
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
                
                if update_clause:
                    query = (
                        f"INSERT INTO {table_name} ({columns_sql}) VALUES ({placeholders}) "
                        f"ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_clause}"
                    )
                else:
                    query = (
                        f"INSERT INTO {table_name} ({columns_sql}) VALUES ({placeholders}) "
                        f"ON CONFLICT ({conflict_cols}) DO NOTHING"
                    )
            
            if not self.db_manager.conn:
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
                            # 日期时间类型：确保格式化为字符串并加引号
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
                    # INSERT ... ON CONFLICT（已在上面构建 query）
                    # 需要为每个批次构建完整的 SQL
                    placeholders = ', '.join(['?' for _ in columns])
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
                
                self.db_manager.conn.execute(batch_query)
            
            if callback:
                callback(table_name, len(data_list))
                
        except Exception as e:
            logger.error(f"直接写入失败 (表: {table_name}): {e}")
            raise
    
    def flush(self, table_name: Optional[str] = None):
        """
        立即刷新指定表或所有表的数据
        
        Args:
            table_name: 表名，None 表示刷新所有表
        """
        if not self.enable:
            return
        
        with self._lock:
            if table_name:
                if table_name in self._queues:
                    self._flush_table(table_name)
            else:
                # 刷新所有表
                tables = list(self._queues.keys())
                for table in tables:
                    self._flush_table(table)
        
        # 触发写入线程检查
        self._flush_event.set()
    
    def wait_for_writes(self, timeout: float = 30.0):
        """
        等待所有写入完成
        
        Args:
            timeout: 超时时间（秒）
        """
        if not self.enable:
            return
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self._lock:
                if not self._queues:
                    return
            
            # 触发刷新
            self._flush_event.set()
            time.sleep(0.1)
        
        # 超时后强制刷新
        logger.warning(f"等待写入超时（{timeout}秒），强制刷新")
        self.flush()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            pending_requests = sum(len(requests) for requests in self._queues.values())
            pending_rows = sum(
                len(req.data_list)
                for requests in self._queues.values()
                for req in requests
            )
        
        return {
            **self._stats,
            'pending_requests': pending_requests,
            'pending_rows': pending_rows,
            'is_running': self._is_running
        }
    
    def shutdown(self):
        """关闭队列，刷新所有数据"""
        if not self.enable:
            return
        
        logger.info("正在关闭批量写入队列...")
        
        # 停止写入线程
        self._is_running = False
        self._stop_event.set()
        self._flush_event.set()
        
        # 等待线程结束
        if self._write_thread and self._write_thread.is_alive():
            self._write_thread.join(timeout=5.0)
        
        # 刷新所有剩余数据
        self.flush()
        
        # 等待所有写入完成
        self.wait_for_writes(timeout=10.0)
        
        logger.info("批量写入队列已关闭")


__all__ = ['BatchWriteQueue', 'WriteRequest']
