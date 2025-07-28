#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import time
from queue import Queue, Empty
from loguru import logger
from utils.db.thread_safe_db_manager import get_thread_safe_db_manager


class DatabaseWriter:
    """
    数据库写入队列管理器
    使用单线程处理所有数据库写入操作，避免并发写入问题
    """
    
    def __init__(self, batch_size=100, flush_interval=5):
        """
        初始化数据库写入器
        
        Args:
            batch_size: 批量写入大小
            flush_interval: 强制刷新间隔（秒）
        """
        self.write_queue = Queue()
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.db_manager = get_thread_safe_db_manager()
        
        # 写入统计
        self.stats = {
            'total_writes': 0,
            'batch_writes': 0,
            'flush_writes': 0,
            'errors': 0
        }
        
        # 启动写入线程
        self.writer_thread = threading.Thread(target=self._writer_worker, daemon=True)
        self.writer_thread.start()
        
        # 停止标志
        self.stop_flag = False
        
        logger.info(f"数据库写入器已启动，批量大小: {batch_size}, 刷新间隔: {flush_interval}秒")
    
    def queue_write(self, table_name, data_list, operation='insert'):
        """
        将写入操作加入队列
        
        Args:
            table_name: 表名
            data_list: 数据列表
            operation: 操作类型 ('insert', 'update', 'delete')
        """
        write_task = {
            'table_name': table_name,
            'data_list': data_list,
            'operation': operation,
            'timestamp': time.time()
        }
        
        self.write_queue.put(write_task)
        self.stats['total_writes'] += 1
    
    def _writer_worker(self):
        """写入工作线程"""
        batch_data = []
        last_flush_time = time.time()
        
        logger.info("数据库写入工作线程已启动")
        
        while not self.stop_flag:
            try:
                # 尝试从队列获取数据，设置超时以便定期检查停止标志
                try:
                    write_task = self.write_queue.get(timeout=1)
                    batch_data.append(write_task)
                except Empty:
                    # 队列为空，检查是否需要强制刷新
                    current_time = time.time()
                    if batch_data and (current_time - last_flush_time) >= self.flush_interval:
                        logger.debug(f"强制刷新 {len(batch_data)} 个写入任务")
                        self._flush_batch(batch_data)
                        batch_data = []
                        last_flush_time = current_time
                    continue
                
                # 检查是否需要批量写入
                if len(batch_data) >= self.batch_size:
                    logger.debug(f"批量写入 {len(batch_data)} 个任务")
                    self._flush_batch(batch_data)
                    batch_data = []
                    last_flush_time = time.time()
                
            except Exception as e:
                logger.error(f"写入工作线程发生错误: {e}")
                self.stats['errors'] += 1
        
        # 处理剩余的数据
        if batch_data:
            logger.info(f"处理剩余 {len(batch_data)} 个写入任务")
            self._flush_batch(batch_data)
        
        logger.info("数据库写入工作线程已停止")
    
    def _flush_batch(self, batch_data):
        """
        批量处理写入任务
        
        Args:
            batch_data: 批量数据列表
        """
        if not batch_data:
            return
        
        # 按表名分组
        table_groups = {}
        for task in batch_data:
            table_name = task['table_name']
            if table_name not in table_groups:
                table_groups[table_name] = []
            table_groups[table_name].append(task)
        
        # 逐表处理
        for table_name, tasks in table_groups.items():
            try:
                self._process_table_batch(table_name, tasks)
                self.stats['batch_writes'] += 1
            except Exception as e:
                logger.error(f"处理表 {table_name} 的批量写入失败: {e}")
                self.stats['errors'] += 1
    
    def _process_table_batch(self, table_name, tasks):
        """
        处理单个表的批量写入
        
        Args:
            table_name: 表名
            tasks: 任务列表
        """
        # 合并所有数据
        all_data = []
        for task in tasks:
            all_data.extend(task['data_list'])
        
        if not all_data:
            return
        
        # 构建批量插入SQL
        if all_data:
            columns = list(all_data[0].keys())
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(columns)
            
            sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
            
            # 准备数据
            values = []
            for data in all_data:
                row_values = [data.get(col) for col in columns]
                values.append(row_values)
            
            # 执行批量插入
            cursor = self.db_manager.get_cursor()
            try:
                cursor.executemany(sql, values)
                logger.debug(f"成功批量插入 {len(all_data)} 条数据到表 {table_name}")
            except Exception as e:
                logger.error(f"批量插入到表 {table_name} 失败: {e}")
                raise
            finally:
                cursor.close()
    
    def flush(self):
        """强制刷新所有待写入的数据"""
        logger.info("强制刷新所有待写入数据")
        self.stats['flush_writes'] += 1
        
        # 等待队列清空
        while not self.write_queue.empty():
            time.sleep(0.1)
        
        # 等待写入线程处理完所有数据
        time.sleep(0.5)
    
    def stop(self):
        """停止写入器"""
        logger.info("正在停止数据库写入器...")
        self.stop_flag = True
        
        # 等待写入线程结束
        if self.writer_thread.is_alive():
            self.writer_thread.join(timeout=10)
        
        # 关闭数据库连接
        self.db_manager.close_all_connections()
        
        logger.info("数据库写入器已停止")
    
    def get_stats(self):
        """获取写入统计信息"""
        return self.stats.copy()
    
    def __del__(self):
        """析构函数，确保停止写入器"""
        if hasattr(self, 'stop_flag') and not self.stop_flag:
            self.stop()


# 全局数据库写入器实例
_database_writer = None
_database_writer_lock = threading.Lock()


def get_database_writer():
    """获取全局数据库写入器实例"""
    global _database_writer
    if _database_writer is None:
        with _database_writer_lock:
            if _database_writer is None:
                _database_writer = DatabaseWriter()
    return _database_writer


def stop_database_writer():
    """停止全局数据库写入器"""
    global _database_writer
    if _database_writer is not None:
        with _database_writer_lock:
            if _database_writer is not None:
                _database_writer.stop()
                _database_writer = None 